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

#include <stdlib.h>
#include <string>

#include "converter.h"
#include "convertor/transform_help.h"
#include "edge_worker.h"
#include "utils/string_util.h"

#include "glog/logging.h"

namespace galileo {
namespace convertor {

AllocIdManager EdgeWorker::alloc_id_manager_;

bool EdgeWorker::ParseRecord(std::vector<std::vector<char*>>& fields) {
  uint8_t etype = galileo::utils::strToUInt8(fields[0][0]);

  int entity1_idx = converter_->schema_.GetEFieldIdx(etype, SCM_ENTITY_1);
  assert(1 == fields[entity1_idx].size());
  char* entity_1 = fields[entity1_idx][0];
  std::string entity1_dtype =
      converter_->schema_.GetEFieldDtype(etype, entity1_idx);
  int partitions = converter_->slice_count_;
  int slice_id = TransformHelp::GetSliceId(entity_1, entity1_dtype, partitions);
  if (slice_id < 0) {
    LOG(ERROR) << "get the edge slice id fail,the entity_1 dtype is"
               << entity1_dtype;
    return false;
  }
  if (!TransformHelp::TransformEdge(converter_->schema_, fields, record_)) {
    return false;
  }

  return this->WriteRecord(slice_id, record_);
}

}  // namespace convertor
}  // namespace galileo
