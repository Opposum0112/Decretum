# Build a User Service

## Domain
software_engineering

## Objective
Build and validate a small Python service.

## Capabilities
- source.read
- source.modify
- test.execute

## Inputs
- Existing Python source tree

## Outputs
- Tested service
- Test results

## Profiles
infrastructure: local-dev
testing: pytest

## Experiments

### Implement Service
objective: implement the service
capabilities: source.read, source.modify
outputs: source

### Run Tests
objective: run the test suite
capabilities: test.execute
depends_on: implement-service
outputs: test-results
