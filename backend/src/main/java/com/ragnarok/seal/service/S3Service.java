package com.ragnarok.seal.service;

import com.ragnarok.seal.config.properties.AwsProperties;
import com.ragnarok.seal.dto.PresignedUrlResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.PresignedPutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.model.PutObjectPresignRequest;

import java.time.Duration;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class S3Service {

    private static final Duration PRESIGN_DURATION = Duration.ofMinutes(15);

    private final S3Presigner s3Presigner;
    private final AwsProperties awsProperties;

    /**
     * Tạo presigned PUT URL để frontend upload file trực tiếp lên S3.
     *
     * @param fileName tên file gốc từ frontend
     * @return PresignedUrlResponse chứa URL và fileKey
     */
    public PresignedUrlResponse generatePresignedUrl(String fileName) {
        String fileKey = UUID.randomUUID() + "/" + fileName;
        log.info("Generating presigned URL for fileKey: {}", fileKey);

        PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                .bucket(awsProperties.getS3().getBucketName())
                .key(fileKey)
                .build();

        PutObjectPresignRequest presignRequest = PutObjectPresignRequest.builder()
                .signatureDuration(PRESIGN_DURATION)
                .putObjectRequest(putObjectRequest)
                .build();

        PresignedPutObjectRequest presignedRequest = s3Presigner.presignPutObject(presignRequest);
        String presignedUrl = presignedRequest.url().toString();

        log.debug("Presigned URL generated successfully for fileKey: {}, expires in {} minutes",
                fileKey, PRESIGN_DURATION.toMinutes());

        return new PresignedUrlResponse(presignedUrl, fileKey);
    }
}
