from app.core.db import Base


def main() -> None:
    print("@startuml")
    for table in Base.metadata.sorted_tables:
        print(f"entity {table.name} {{")
        for column in table.columns:
            marker = "* " if column.primary_key else ""
            print(f"  {marker}{column.name}: {column.type}")
        print("}")
    print("@enduml")


if __name__ == "__main__":
    main()
