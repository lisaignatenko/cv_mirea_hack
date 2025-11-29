"""Console entrypoint for database migrations."""

from back.data.migrations import run_migrations


def main() -> None:
    run_migrations()


if __name__ == "__main__":
    main()
