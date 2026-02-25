# java project standards

## version
- java 21+ (use virtual threads, pattern matching, records, sealed interfaces)

## build tool
- gradle (kotlin dsl) preferred, maven acceptable

## project structure
```
project-name/
├── build.gradle.kts
├── settings.gradle.kts
├── src/
│   ├── main/java/com/pradyum/projectname/
│   │   ├── domain/             # entities, value objects, domain services
│   │   │   ├── model/
│   │   │   └── service/
│   │   ├── application/        # use cases, ports
│   │   │   ├── port/
│   │   │   │   ├── in/         # driving ports (interfaces)
│   │   │   │   └── out/        # driven ports (interfaces)
│   │   │   └── usecase/
│   │   ├── infrastructure/     # adapters, config, persistence
│   │   │   ├── adapter/
│   │   │   │   ├── in/         # controllers, cli
│   │   │   │   └── out/        # repo implementations, clients
│   │   │   └── config/
│   │   └── Application.java
│   └── test/java/com/pradyum/projectname/
│       ├── unit/
│       └── integration/
├── .env.example
├── .gitignore
└── Makefile
```

## code style
- records for immutable data carriers (not classes with getters)
- sealed interfaces for type hierarchies
- pattern matching with switch expressions
- virtual threads for concurrent i/o operations
- Optional for nullable returns (never null for public API)
- streams for collection transformations (but don't over-chain)

## patterns
- hexagonal architecture (ports & adapters) for anything non-trivial
- builder pattern for complex object construction
- strategy pattern over switch statements for behavior variation
- factory methods over constructors for polymorphic creation

## dependency injection
- constructor injection only (no field injection)
- if using spring: @Component scanning with explicit @Bean config for infra
- if no framework: manual wiring in a composition root

## testing
- junit 5 + assertj for assertions
- mockito for mocking (verify sparingly — test behavior, not implementation)
- testcontainers for integration tests with real databases
