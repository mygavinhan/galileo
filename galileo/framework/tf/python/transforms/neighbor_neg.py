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
from galileo.framework.tf.python.ops import TFOps as ops
from galileo.platform.export import export


@export('galileo.tf')
class NeighborNegTransform(BaseTransform):
    r'''
    \brief neighbor with negative sampling
    '''
    def __init__(self, vertex_type: list, edge_types: list, negative_num: int,
                 **kwargs):
        r'''
        \param vertex_type
        \param edge_types
        \param negative_num
        '''
        config = dict(vertex_type=vertex_type,
                      edge_types=edge_types,
                      negative_num=negative_num)
        super().__init__(config=config)

    def transform(self, inputs):
        r'''
        \param inputs vertices
        \return dict(target=tensor,context=tensor,negative=tensor)
        '''
        vertex_type = self.config['vertex_type']
        edge_types = self.config['edge_types']
        negative_num = self.config['negative_num']

        if not tf.is_tensor(inputs):
            inputs = tf.convert_to_tensor(inputs, dtype=tf.int64)
        context = ops.sample_neighbors(tf.reshape(inputs, [-1]),
                                       edge_types,
                                       count=1,
                                       has_weight=False)
        if len(context) == 0:
            raise ValueError('Error sample neighbors, see logs for details')
        target = tf.reshape(inputs, [-1, 1])
        context = tf.reshape(context[0], [-1, 1])
        size = tf.size(target)
        negative = ops.sample_vertices(types=vertex_type,
                                       count=size * negative_num)[0]
        negative = tf.reshape(negative, [size, negative_num])
        return dict(target=target, context=context, negative=negative)
