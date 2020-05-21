# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2020 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging
from functools import partial

from django.utils.translation import ugettext_lazy as _

from gcloud.conf import settings
from gcloud.utils.handlers import handle_api_error

logger = logging.getLogger('celery')
get_client_by_user = settings.ESB_GET_CLIENT_BY_USER

__group_name__ = _("配置平台(CMDB)")

cc_handle_api_error = partial(handle_api_error, __group_name__)


def cc_get_host_id_by_innerip(executor, bk_biz_id, ip_list, supplier_account):
    """
    获取主机ID
    :param executor:
    :param bk_biz_id:
    :param ip_list:
    :return: [1, 2, 3] id列表
    """
    cc_kwargs = {
        'bk_biz_id': bk_biz_id,
        'bk_supplier_account': supplier_account,
        'ip': {
            'data': ip_list,
            'exact': 1,
            'flag': 'bk_host_innerip'
        },
        'condition': [
            {
                'bk_obj_id': 'host',
                'fields': ['bk_host_id', 'bk_host_innerip']
            }
        ],
    }

    client = get_client_by_user(executor)
    cc_result = client.cc.search_host(cc_kwargs)

    if not cc_result['result']:
        message = cc_handle_api_error('cc.search_host', cc_kwargs, cc_result)
        return {'result': False, 'message': message}

    # change bk_host_id to str to use str.join() function
    ip_to_id = {item['host']['bk_host_innerip']: str(item['host']['bk_host_id']) for item in cc_result['data']['info']}
    host_id_list = []
    invalid_ip_list = []
    for ip in ip_list:
        if ip in ip_to_id:
            host_id_list.append(ip_to_id[ip])
        else:
            invalid_ip_list.append(ip)

    if invalid_ip_list:
        result = {
            'result': False,
            'message': _("查询配置平台(CMDB)接口cc.search_host表明，存在不属于当前业务的IP: {ip}").format(
                ip=','.join(invalid_ip_list)
            )
        }
        return result
    return {'result': True, 'data': host_id_list}


def get_module_set_id(topo_data, module_id):
    """
    获取模块属于的集群ID
    :param topo_data:
    :param module_id:
    :return:
    """
    for item in topo_data:
        if item['bk_obj_id'] == "set" and item.get('child'):
            set_id = item['bk_inst_id']
            for mod in item['child']:
                if mod['bk_inst_id'] == module_id:
                    return set_id

        if item.get('child'):
            set_id = get_module_set_id(item['child'], module_id)
            if set_id:
                return set_id


def cc_format_prop_data(executor, obj_id, prop_id, language, supplier_account):
    ret = {
        "result": True,
        "data": {}
    }
    client = get_client_by_user(executor)
    if language:
        setattr(client, 'language', language)
    cc_kwargs = {
        "bk_obj_id": obj_id,
        "bk_supplier_account": supplier_account
    }

    cc_result = client.cc.search_object_attribute(cc_kwargs)
    if not cc_result['result']:
        message = cc_handle_api_error('cc.search_object_attribute', cc_kwargs, cc_result)
        ret['result'] = False
        ret['message'] = message
        return ret

    for prop in cc_result['data']:
        if prop['bk_property_id'] == prop_id:
            for item in prop['option']:
                ret['data'][item['name'].strip()] = item['id']
            else:
                break
    return ret


def cc_format_tree_mode_id(front_id_list):
    if front_id_list is None:
        return []
    return [int(str(x).split('_')[1]) if len(str(x).split('_')) == 2 else int(x) for x in front_id_list]


def cc_parse_path_text(path_text):
    """
    将目标主机/模块/自定义层级的文本路径解析为列表形式，支持空格/空行容错解析
    :param path_text: 目标主机/模块/自定义层级的文本路径
    :return:路径列表，每个路径是一个节点列表
    example:
    a > b > c > s
       a>v>c
    a
    解析结果
    [
        [a, b, c, s],
        [a, v, c],
        [a]
    ]
    """
    text_path_list = path_text.split('\n')
    path_list = []
    for text_path in text_path_list:
        text_path = text_path.strip()
        path = []
        if len(text_path) != 0:
            for text_node in text_path.split('>'):
                text_node = text_node.strip()
                if len(text_node) != 0:
                    path.append(text_node)
            path_list.append(path)
    return path_list


def cc_list_match_node_inst_id(topo_tree, path_list):
    """
    路径匹配，对path_list中的所有路径与拓扑树进行路径匹配
    :param topo_tree: 业务拓扑 list
    [
        {
            "bk_inst_id": 2,
            "bk_inst_name": "blueking",
            "bk_obj_id": "biz",
            "bk_obj_name": "business",
            "child": [
                {
                    "bk_inst_id": 3,
                    "bk_inst_name": "job",
                    "bk_obj_id": "set",
                    "bk_obj_name": "set",
                    "child": [
                        {
                            "bk_inst_id": 5,
                            "bk_inst_name": "job",
                            "bk_obj_id": "module",
                            "bk_obj_name": "module",
                            "child": []
                        },
                        {
                            ...
                        }
                    ]
                }
            ]
        }
    ]
    :param path_list: 路径列表，example: [[a, b], [a, c]]
    :return:
        True: list -匹配父节点的bk_inst_id
        False: message -错误信息
    """
    inst_id_list = []
    for path in path_list:
        index = 0
        topo_node_list = topo_tree
        while len(path) > index:
            match_node = None
            for topo_node in topo_node_list:
                if path[index] == topo_node['bk_inst_name']:
                    match_node = topo_node
                    break
            if match_node:
                index = index + 1
                if index == len(path):
                    inst_id_list.append(match_node['bk_inst_id'])
                topo_node_list = match_node['child']
            else:
                return {'result': False, 'message': _('不存在该拓扑路径：{}').format('>'.join(path))}
    return {'result': True, 'data': inst_id_list}