package com.ragnarok.seal;

import com.ragnarok.seal.config.properties.AiServiceProperties;
import com.ragnarok.seal.config.properties.AwsProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties({ AwsProperties.class, AiServiceProperties.class })
public class SealApplication {

	public static void main(String[] args) {
		SpringApplication.run(SealApplication.class, args);
	}

}
