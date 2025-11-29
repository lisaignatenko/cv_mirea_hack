import uvicorn


def main() -> None:
    uvicorn.run("back.api.app:app", host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
