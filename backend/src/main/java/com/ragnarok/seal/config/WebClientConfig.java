package com.ragnarok.seal.config;

import com.ragnarok.seal.config.properties.AiServiceProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.WebClient;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class WebClientConfig {

    private final AiServiceProperties aiServiceProperties;

    @Bean
    public WebClient aiServiceWebClient() {
        log.info("Initializing WebClient for AI Service at: {}", aiServiceProperties.getBaseUrl());

        return WebClient.builder()
                .baseUrl(aiServiceProperties.getBaseUrl())
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .build();
    }
}
