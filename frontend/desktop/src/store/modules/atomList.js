/**
* Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
* Edition) available.
* Copyright (C) 2017-2019 THL A29 Limited, a Tencent company. All rights reserved.
* Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
* http://opensource.org/licenses/MIT
* Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
* an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
* specific language governing permissions and limitations under the License.
*/
import api from '../../api/index.js'

const atomList = {
    namespaced: true,
    state: {
        singleAtom: [],
        subAtom: []
    },
    mutations: {
        setSingleAtom (state, data) {
            state.singleAtom = [...data]
        },
        setSubAtom (state, data) {
            state.subAtom = [...data]
        }
    },
    actions: {
        loadSingleAtomList ({ commit }) {
            return api.getSingleAtomList().then(response => response.data.objects)
        },
        loadSubflowList ({ commit }, data) {
            return api.getSubAtomList(data).then(response => response.data.objects)
        },
        queryAtomData ({ commit }, data) {
            return api.queryAtom(data).then(response => response.data)
        }
    },
    getters: {
        singleAtomGrouped (state) {
            const primaryData = state.singleAtom
            const groups = []
            const atomGrouped = []
            primaryData.forEach(item => {
                const type = item.group_name
                const index = groups.indexOf(type)
                // 分组存在
                if (index > -1) {
                    const list = atomGrouped[index].list
                    const isCodeExisted = list.some(m => m.code === item.code)
                    // 相同 code 的只显示一个
                    if (!isCodeExisted) {
                        list.push(item)
                    }
                } else {
                    const newGroup = {
                        type,
                        group_name: item.group_name,
                        group_icon: item.group_icon,
                        list: [item]
                    }
                    groups.push(type)
                    atomGrouped.push(newGroup)
                }
            })
            return [...atomGrouped]
        }
    }
}

export default atomList
