# MVP Definition

Many projects fail because the MVP is too large. Our MVP is **not AI**.

## MVP Core Flow

```mermaid
flowchart TD
    A[User enters GitHub repository URL] --> B[Repository clones]
    B --> C[Tree-sitter parses files]
    C --> D[Extract functions]
    D --> E[Extract classes]
    E --> F[Extract imports]
    F --> G[Store in PostgreSQL]
    G --> H[Build dependency graph in Neo4j]
    H --> I[Visualize graph]
    I --> J[Done]
```

## Constraints (Out of Scope for MVP)

- **No chat**
- **No AI agents**
- **No predictions**

*Those come later.*
