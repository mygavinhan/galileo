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
'''
使用原生PyTorch训练Node2vec模型
'''

import os
import argparse
import torch
import galileo as g
import galileo.pytorch as gp


class Node2vec(gp.Unsupervised):
    def __init__(self, embedding_size, embedding_dim, **kwargs):
        super().__init__(**kwargs)
        self._target_encoder = gp.Embedding(embedding_size, embedding_dim,
                                            **kwargs)
        self._context_encoder = self._target_encoder

    def target_encoder(self, inputs):
        return self._target_encoder(inputs)

    def context_encoder(self, inputs):
        return self._context_encoder(inputs)


class Inputs(g.BaseInputs):
    def __init__(self, **kwargs):
        super().__init__(config=kwargs)

    def transform(self, inputs):
        vertex_type = self.config['vertex_type']
        edge_types = self.config['edge_types']
        context_size = self.config['context_size']
        negative_num = self.config['negative_num']
        walk_length = self.config['walk_length']
        repetition = self.config['repetition']
        walk_p = self.config['walk_p']
        walk_q = self.config['walk_q']
        metapath = [edge_types] * walk_length

        if not torch.is_tensor(inputs):
            inputs = torch.tensor(inputs)
        vertices = inputs.view(-1)
        pair = gp.ops.sample_pairs_by_random_walk(vertices=vertices,
                                                  metapath=metapath,
                                                  repetition=repetition,
                                                  context_size=context_size,
                                                  p=walk_p,
                                                  q=walk_q)
        target, context = torch.split(pair, [1, 1], dim=-1)
        negative = gp.ops.sample_vertices(types=vertex_type,
                                          count=negative_num * pair.size(0))[0]
        negative = negative.view(pair.size(0), negative_num)
        return {'target': target, 'context': context, 'negative': negative}

    def train_data(self):
        return gp.dataset_pipeline(gp.VertexDataset, self.transform,
                                   **self.config)

    def evaluate_data(self):
        return gp.dataset_pipeline(
            lambda **kwargs: gp.RangeDataset(start=1708, end=2707, **kwargs),
            self.transform, **self.config)

    def predict_data(self):
        return gp.dataset_pipeline(
            lambda **kwargs: gp.RangeDataset(
                start=0, end=kwargs['max_id'], **kwargs),
            lambda inputs: {'target': torch.tensor(inputs)}, **self.config)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max_id', default=2708, type=int, help='max node id')
    parser.add_argument('--gpu', default='0', type=str, help='gpu devices')
    parser.add_argument('--model_dir',
                        default='.models/node2vec_pt',
                        type=str,
                        help='model dir')
    parser = g.define_service_args(parser)
    args, _ = parser.parse_known_args()
    if args.data_source_name is None:
        args.data_source_name = 'cora'
    g.start_service_from_args(args)

    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu

    n2v = Node2vec(
        embedding_size=args.max_id + 1,
        embedding_dim=64,
    )

    inputs = Inputs(batch_size=32,
                    max_id=args.max_id,
                    vertex_type=[0],
                    edge_types=[0],
                    walk_length=3,
                    repetition=5,
                    walk_p=1.,
                    walk_q=1.,
                    context_size=2,
                    negative_num=5)

    g.create_client(args.zk_server, args.zk_path)
    dataloader = inputs.train_data()
    n2v.cuda()
    optimizer = torch.optim.Adam(n2v.parameters(), lr=0.01)
    for i in range(10):
        for subset in dataloader:
            subset = gp.data_to_cuda(subset, 0)
            optimizer.zero_grad()
            outputs = n2v(subset)
            loss = outputs['loss']
            loss.backward()
            optimizer.step()
        print(f'Epoch: {i}, loss: {loss}')


if __name__ == "__main__":
    main()
