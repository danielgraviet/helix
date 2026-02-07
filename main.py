from dotenv import load_dotenv
load_dotenv()

from rich.console import Console # noqa: E402

from orchestrator.agent import run_agent # noqa: E402
from orchestrator.registry import SkillRegistry # noqa: E402
from skill_factory.factory import remove_skill  # noqa: E402

console = Console()


def cleanup(registry: SkillRegistry) -> None:
    """Stop and remove all running skill containers."""
    skills = registry.list_skills()
    if not skills:
        return
    console.print(f"[yellow]Cleaning up {len(skills)} skill container(s)...[/yellow]")
    for skill_info in skills:
        skill = registry.lookup(skill_info["name"])
        if skill:
            try:
                remove_skill(skill)
                console.print(f"  Removed {skill.name}")
            except Exception:
                pass


def main():
    console.print("[bold]Helix — Skills that evolve on demand.[/bold]")
    console.print("Type a task and the agent will create skills to solve it.")
    console.print("Type 'quit' to exit.\n")

    registry = SkillRegistry()

    try:
        while True:
            user_input = console.input("[bold green]> [/bold green]").strip()

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                break

            try:
                response = run_agent(user_input, registry)
                console.print(f"\n[bold]{response}[/bold]\n")
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]\n")
    except KeyboardInterrupt:
        console.print("\n")
    finally:
        cleanup(registry)
        console.print("[dim]Goodbye.[/dim]")


if __name__ == "__main__":
    main()
