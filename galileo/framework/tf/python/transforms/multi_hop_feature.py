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
from galileo.framework.tf.python.ops import TFOps as ops
from galileo.platform.export import export
from .multi_hop import MultiHopNeighborTransform


@export('galileo.tf')
class MultiHopFeatureTransform(MultiHopNeighborTransform):
    r'''
    \brief transform for multi hop features

    \par Examples:
    \code{.py}
        >>> from galileo.tf import MultiHopFeatureTransform
        >>> transform = MultiHopFeatureTransform([[0],[0]],[2,3],
                False,['feature'],5).transform
        >>> res = transform([2,4])
        >>> res.keys()
        dict_keys(['ids', 'dense'])
        >>> res['ids'].shape
        TensorShape([2, 9])
        >>> res['dense'].shape
        TensorShape([2, 9, 5])
    \endcode
    '''
    def __init__(
        self,
        metapath: list,
        fanouts: list,
        edge_weight: bool = False,
        dense_feature_names: list = None,
        dense_feature_dims=None,
        sparse_feature_names: list = None,
        sparse_feature_dims=None,
        **kwargs,
    ):
        r'''
        \param metapath list of list, edge types of multi hop
        \param fanouts number of multi hop
        \param edge_weight has weight or not
        \param dense_feature_names list of str
        \param dense_feature_dims int or list[int]
        \param sparse_feature_names list of str
        \param sparse_feature_dims int or list[int]
        '''
        if dense_feature_names is None and sparse_feature_names is None:
            raise ValueError('one of dense or sparse feature '
                             'names must be specified')
        if dense_feature_names is not None:
            assert dense_feature_dims, ('must set dense_feature_dims'
                                        '(int or list[int])')
            if isinstance(dense_feature_dims, int):
                dense_feature_dims = [dense_feature_dims
                                      ] * len(dense_feature_names)
            assert len(dense_feature_names) == len(dense_feature_dims)
        if sparse_feature_names is not None:
            if sparse_feature_dims is None:
                sparse_feature_dims = 1
            if isinstance(sparse_feature_dims, int):
                sparse_feature_dims = [sparse_feature_dims
                                       ] * len(sparse_feature_names)
            for dim in sparse_feature_dims:
                if dim != 1:
                    raise ValueError('Only support one dim sparse feature')
            assert len(sparse_feature_names) == len(sparse_feature_dims)
        super().__init__(metapath,
                         fanouts,
                         edge_weight,
                         dense_feature_names=dense_feature_names,
                         dense_feature_dims=dense_feature_dims,
                         sparse_feature_names=sparse_feature_names,
                         sparse_feature_dims=sparse_feature_dims,
                         **kwargs)

    def transform(self, inputs):
        r'''
        \param inputs vertices
        \return
        dict(ids=tensor, dense=tensor, sparse=tensor, edge_weight=tensor)
        '''
        edge_weight = self.config['edge_weight']
        dense_feature_names = self.config['dense_feature_names']
        dense_feature_dims = self.config['dense_feature_dims']
        sparse_feature_names = self.config['sparse_feature_names']
        sparse_feature_dims = self.config['sparse_feature_dims']

        multi_hops = self.sample_multi_hop(inputs)
        outputs = dict(ids=multi_hops[0])
        vertices_flat = tf.reshape(multi_hops[0], [-1])
        vertices, indices = tf.unique(vertices_flat)
        dense_features = self.get_feature(
            vertices,
            dense_feature_names,
            dense_feature_dims,
            tf.float32,
            indices,
            tf.shape(multi_hops[0]),
        )
        if dense_features is not None:
            outputs['dense'] = dense_features
        sparse_features = self.get_feature(
            vertices,
            sparse_feature_names,
            sparse_feature_dims,
            tf.int64,
            indices,
            tf.shape(multi_hops[0]),
        )
        if sparse_features is not None:
            outputs['sparse'] = sparse_features
        if edge_weight:
            outputs['edge_weight'] = multi_hops[1]
        return outputs

    def get_feature(
        self,
        vertices,
        feature_names,
        feature_dims,
        feature_type,
        indices=None,
        origin_shape=None,
    ):
        if feature_names is None:
            return None
        features = ops.get_pod_feature([vertices], feature_names, feature_dims,
                                       [feature_type] * len(feature_names))
        features = tf.concat(features, axis=-1)
        if indices is not None:
            features = tf.gather(features, indices)
            if origin_shape is not None:
                output_shape = tf.concat([origin_shape, [sum(feature_dims)]],
                                         axis=0)
                features = tf.reshape(features, output_shape)
        return features
