package com.ragnarok.seal.config;

import com.ragnarok.seal.config.properties.AwsProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class AwsConfig {

    private final AwsProperties awsProperties;

    @Bean
    public S3Client s3Client() {
        log.info("Initializing S3Client for region: {}, bucket: {}",
                awsProperties.getS3().getRegion(),
                awsProperties.getS3().getBucketName());

        return S3Client.builder()
                .region(Region.of(awsProperties.getS3().getRegion()))
                .credentialsProvider(staticCredentialsProvider())
                .build();
    }

    @Bean
    public S3Presigner s3Presigner() {
        log.info("Initializing S3Presigner for region: {}", awsProperties.getS3().getRegion());

        return S3Presigner.builder()
                .region(Region.of(awsProperties.getS3().getRegion()))
                .credentialsProvider(staticCredentialsProvider())
                .build();
    }

    private StaticCredentialsProvider staticCredentialsProvider() {
        return StaticCredentialsProvider.create(
                AwsBasicCredentials.create(
                        awsProperties.getCredentials().getAccessKey(),
                        awsProperties.getCredentials().getSecretKey()));
    }
}
