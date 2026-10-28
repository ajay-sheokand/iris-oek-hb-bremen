from app.runners.compensation_sites_runner import run


def main():
    summary = run()
    print(summary)


if __name__ == "__main__":
    main()