"""Retired inactivity scheduler; retained as a harmless compatibility entry point."""

def tick(last_completed_day, *, now=None):
    return last_completed_day


def main():
    print('Account inactivity checking and Telegram reporting are disabled.', flush=True)


if __name__ == '__main__':
    main()
