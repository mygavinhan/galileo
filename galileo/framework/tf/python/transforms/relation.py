# Copyright 2020 JD.com, Inc. Galileo Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import tensorflow as tf
from galileo.framework.python.base_transform import BaseTransform
from galileo.framework.python.utils.utils import (
    get_fanouts_list,
    get_fanouts_indices,
)
from galileo.platform.export import export


@export('galileo.tf')
class RelationTransform(BaseTransform):
    r'''
    \brief transform multi hops to relation graph

    \details
    a relation graph is a dict:
    \code{.py}
        dict(
            relation_indices=tensor,
            relation_weight=tensor,
            target_indices=tensor,
        )
    \endcode

    relation_indices is a [2,E] int tensor, E is number of edges,\n
        indices of relation/edge of graph
    relation_weight is a [E,1] float tensor, weight of relation\n
    target_indices is indices of target vertices, [batch size]

    \par Examples
    \code{.py}
        >>> from galileo.tf import RelationTransform
        >>> # fanouts= [2,3] batch size=5 num nodes=10
        >>> ids = tf.random.uniform([5, 9], maxval=10, dtype=tf.int32)
        >>> ids, indices = tf.unique(tf.reshape(ids, [-1]))
        >>> rt = RelationTransform([2,3])
        >>> res = rt.transform(dict(indices=indices,
                    edge_weight=tf.random.normal((5,9))))
        >>> res.keys()
        dict_keys([relation_indices', 'relation_weight', 'target_indices'])
        >>> res['relation_indices'].shape
        TensorShape([2, 40])
        >>> res['relation_weight'].shape
        TensorShape([40, 1])
        >>> res['target_indices'].shape
        TensorShape([5])
    \endcode
    '''
    def __init__(self, fanouts: list, sort_indices: bool = False, **kwargs):
        r'''
        \param fanouts number of multi hop
        \param sort_indices sort relation indices
        '''
        assert fanouts, 'fanouts must be specified'
        config = dict(fanouts=fanouts)
        config.update(kwargs)
        super().__init__(config=config)
        self.fanouts = fanouts
        self.fanouts_list = get_fanouts_list(fanouts)
        self.fanouts_dim = sum(self.fanouts_list)
        self.fanouts_indices = get_fanouts_indices(fanouts)
        self.sort_indices = sort_indices

    def transform(self, inputs):
        r'''
        \param inputs
            list or tuple or \n
            dict(indices=tensor, edge_weight=tensor)\n
            size of indices and edge_weight must be N * fanouts_dim

        \return
            dict(
                relation_indices=tensor,
                relation_weight=tensor,
                target_indices=tensor,
            )
        '''
        if isinstance(inputs, (list, tuple)):
            indices, edge_weight = inputs[:2]
        elif isinstance(inputs, dict):
            indices = inputs['indices']
            edge_weight = inputs.get('edge_weight')
        else:
            indices, edge_weight = inputs, None

        with tf.name_scope('relation_transform'):
            # convert indices to relation indices
            indices_t = tf.transpose(
                tf.reshape(indices, [-1, self.fanouts_dim]))
            if indices.shape.rank > 2:
                shp = tf.shape(indices)[:indices.shape.rank - 1]
                target_indices = tf.reshape(indices_t[0], shp)
            else:
                target_indices = indices_t[0]
            relation_indices = tf.gather(indices_t, self.fanouts_indices)
            relation_indices = tf.concat(tf.split(
                relation_indices,
                len(self.fanouts_indices) // 2),
                                         axis=1)

            if self.sort_indices:
                idx = tf.argsort(tf.gather(relation_indices, 0))
                relation_indices = tf.gather(relation_indices, idx, axis=1)

            relation_weight = None
            if edge_weight is not None:
                relation_weight = tf.reshape(edge_weight[:, 1:], [-1, 1])

        return dict(
            relation_indices=relation_indices,
            relation_weight=relation_weight,
            target_indices=target_indices,
        )
