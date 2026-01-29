# Lessons Learned

Insights and takeaways from building Troller - an autonomous GitHub issue resolution system.

## What Worked

### Skills and Commands for Persona Containment

Using skills (reusable prompt modules) and slash commands helped contain and define different AI personas effectively. Each persona (Planning, Coding, Review) has clear boundaries and responsibilities, making orchestration more predictable and debuggable.

**Key insight:** Modular prompts are easier to iterate on than monolithic system prompts.

### Dogfooding Through Development

Building Troller using AI-assisted development created a powerful feedback loop - using the product to build the product. This "meta" approach surfaced real usability issues and edge cases that wouldn't have been discovered through traditional testing alone.

**Key insight:** Eating your own dogfood accelerates product-market fit, even when the market is yourself.

### Retrospectives and Iterative Persona Refinement

Running retros after development sessions to evaluate what worked and what didn't, then incorporating that feedback directly into the AI personas, created a continuous improvement cycle. The personas evolved based on real-world friction points rather than theoretical design.

**Key insight:** Treat AI personas like team members - they benefit from the same feedback loops humans do.

### Reusable Skills for Coding Standards

Creating skills that define coding style and general development approach served dual purposes:
1. Guided the AI agents during autonomous implementation
2. Provided consistent standards for human-AI collaboration during development

**Key insight:** Skills are a shared language between human developers and AI agents.

## Evolution of the Idea

The project started from a simpler premise: building individual AI agents to augment software development workflow. Over time, the vision evolved:

```
Individual Agents → Coordinated Multi-Agent System → Human-Out-of-Loop Automation
```

The goal shifted from "AI assists human" to "human assists AI (only when necessary)." This inversion required rethinking:
- When to escalate vs. retry autonomously
- How to preserve context across long-running workflows
- What information humans need when they do intervene

## What We'd Do Differently

> [!todo] To be added
> As the project matures, this section will capture approaches we'd change with hindsight.

## Open Questions

- How to balance agent autonomy with appropriate human oversight?
- What's the right granularity for skills - too specific vs. too generic?
- How to measure the quality of AI-generated code beyond "tests pass"?

## Recommendations for Similar Projects

1. **Start with dogfooding** - Use your AI tools to build your AI tools
2. **Invest in skills/prompts as first-class artifacts** - Version them, test them, iterate on them
3. **Build feedback loops early** - Retros aren't just for humans
4. **Design for human escalation** - The goal is autonomous, but the fallback must be seamless
