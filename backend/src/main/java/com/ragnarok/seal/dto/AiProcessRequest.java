package com.ragnarok.seal.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiProcessRequest(
        @JsonProperty("file_key") String fileKey) {
}
