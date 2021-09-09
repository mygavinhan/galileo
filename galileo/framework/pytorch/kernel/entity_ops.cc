// Copyright 2020 JD.com, Inc. Galileo Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// ==============================================================================

#include "../ops/ops.h"

#include "../common/tensor_alloc.h"
#include "engine/client/dgraph_global.h"

using namespace galileo::client;

namespace torch {
namespace glo {

template <typename T>
using ArraySpec = galileo::common::ArraySpec<T>;

Tensors CollectEntity(Tensor types, int32_t count,
                      const std::string& category) {
  if (nullptr == gDGraph) {
    LOG(ERROR) << " Global dgraph instance is nullptr.please init global "
                  "dgraph instance.";
    return {};
  }

  if (types.dim() != 1 || count <= 0 ||
      (category != "vertex" && category != "edge")) {
    LOG(ERROR) << " Collect entity input params error";
    return {};
  }

  auto types_value = types.data_ptr<uint8_t>();
  ArraySpec<uint8_t> spec(types_value, types.numel());

  Dtypes dtypes;
  if (category == "vertex") {
    dtypes.emplace_back(kLong);
  } else if (category == "edge") {
    dtypes.emplace_back(kLong);
    dtypes.emplace_back(kLong);
    dtypes.emplace_back(kByte);
  }

  Tensors tens;
  PTTypedTensorAlloc alloc(tens, dtypes);
  int res = gDGraph->CollectEntity(category, spec, static_cast<uint32_t>(count),
                                   &alloc);
  if (res != static_cast<int>(dtypes.size())) {
    LOG(ERROR) << " Collect entity is failed.input param invalid or graph "
                  "server error."
               << " res:" << res;
    return {};
  }
  return tens;
}

}  // namespace glo
}  // namespace torch
