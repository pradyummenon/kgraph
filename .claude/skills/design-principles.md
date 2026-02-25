# design principles reference

## SOLID

### single responsibility
every class/module does one thing. if you need "and" to describe it, split it.
test: can you describe what a class does in one sentence without using "and"?

### open/closed
extend behavior through composition and polymorphism, not by modifying existing code.
test: can you add a new feature without changing existing classes?

### liskov substitution
subtypes must be substitutable for their base types without breaking correctness.
test: does every subclass honor the contract of its parent?

### interface segregation
no client should depend on methods it doesn't use. prefer small, focused interfaces.
test: does any implementing class have methods that throw "not implemented"?

### dependency inversion
high-level modules depend on abstractions, not concrete implementations.
test: can you swap an implementation without touching business logic?

## GRASP

### information expert
assign responsibility to the class that has the data needed to fulfill it.

### creator
assign object creation to the class that has the initializing data or closely uses it.

### controller
use a dedicated class to handle system events — don't put orchestration in entities.

### low coupling
minimize dependencies between classes. prefer event-driven over direct calls where appropriate.

### high cohesion
keep related behavior together. a class should have a focused, clear purpose.

## key patterns to reach for

| situation | pattern | why |
|-----------|---------|-----|
| varying algorithms | strategy | swap behavior without conditionals |
| complex object creation | builder / factory | separate construction from representation |
| event-driven communication | observer / pub-sub | decouple producers from consumers |
| resource management | proxy / decorator | add behavior without modifying originals |
| complex subsystem | facade | simplify the interface for clients |
| graph traversal strategies | visitor | separate algorithm from structure |

## anti-patterns to reject

- god class: one class that knows/does everything
- service locator: hidden dependencies, untestable
- anemic domain model: entities with only getters/setters, logic elsewhere
- primitive obsession: using strings/ints where value objects belong
- feature envy: methods that use another class's data more than their own
