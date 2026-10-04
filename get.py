import pyautogui


def main() -> None:
    while True:
        position = pyautogui.position()
        print(position)


if __name__ == "__main__":
    main()