import app.models  # noqa: F401  — populates Base.metadata; nothing else imports every model
from app.core.db import Base


def main() -> None:
    print("@startuml")
    for table in Base.metadata.sorted_tables:
        fk_columns = {fk.parent.name for fk in table.foreign_keys}
        print(f"entity {table.name} {{")
        for column in table.columns:
            if column.primary_key:
                marker = "* "
            elif column.name in fk_columns:
                marker = "+ "
            else:
                marker = ""
            nullable = "" if column.nullable else " NOT NULL"
            print(f"  {marker}{column.name}: {column.type}{nullable}")
        print("}")
    for table in Base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            print(f"{table.name} }}o--|| {fk.column.table.name}")
    print("@enduml")


if __name__ == "__main__":
    main()
