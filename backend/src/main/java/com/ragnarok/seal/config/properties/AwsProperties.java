package com.ragnarok.seal.config.properties;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Getter
@Setter
@ConfigurationProperties(prefix = "aws")
public class AwsProperties {

    private S3 s3 = new S3();
    private Credentials credentials = new Credentials();

    @Getter
    @Setter
    public static class S3 {
        private String bucketName;
        private String region;
    }

    @Getter
    @Setter
    public static class Credentials {
        private String accessKey;
        private String secretKey;
    }
}
