from app.models.document import Document

def main():
    document = Document(
        id='001',
        title="Networking notes",
        text="these are networking notes"
    )

    print(document)


if __name__ == "__main__":
    main()