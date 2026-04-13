package com.ragnarok.seal.dto;

public record PresignedUrlResponse(
        String presignedUrl,
        String fileKey) {
}
