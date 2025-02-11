# Little Brother: A Smart Home Security System

**Little Brother** is a comprehensive home security system leveraging computer vision and Deep Learning to provide intelligent home surveillance. It incorporates:

*   **Motion Detection:** Identifies movement within the camera's field of view.
*   **Human (Person) Detection:**  Distinguishes humans from other moving objects.
*   **Face Detection and Recognition:**  Detects faces and identifies known individuals.
*   **Telegram Integration:** Manage room acces and sends notifications, including images, to authorized users via a Telegram bot.

This combination of features allows for a robust and informative security system, alerting you only when necessary and providing specific details about who triggered the alert.

## Installation and Setup

### 1. Prerequisites

*   **Python 3.12+:**  Ensure you have a compatible Python version installed.
*   **uv:**  This project uses `uv` for fast dependency management.  Install it following the instructions at [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/).

### 2. Clone the Repository

```bash
git clone https://github.com/Tommaso-Sgroi/LittleBrother
cd LittleBrother
```

### 3. Install Dependencies
Use `uv` to install the project's dependencies:

```bash
uv sync
```

### 4. Configure Environment Variables (Unix/Linux/macOS)
You need to set two environment variables:

* `TELEGRAM_BOT_TOKEN`: This is the API token for your Telegram bot. You'll need to create a bot with [BotFather](https://t.me/botfather) on Telegram to obtain this token.
* `AUTH_TOKEN`: This is a custom token you choose. It's used to authenticate users within the Telegram bot.

#### Setting Environment Variables (Temporary - for the current terminal session):

```bash
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export AUTH_TOKEN="your_chosen_auth_token"
```

#### Setting Environment Variables (Permanent - using `.bashrc` or `.zshrc`):

1. Open your shell's configuration file (e.g., `~/.bashrc` for Bash, `~/.zshrc` for Zsh) in a text editor:

```bash
nano ~/.bashrc  # Or use your preferred editor (e.g., vim, emacs)
```

2. Add the following lines to the end of the file:

```bash
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export AUTH_TOKEN="your_chosen_auth_token"
```

3. Save the file and close the editor.
4. Source the configuration file to apply the changes:

```bash
source ~/.bashrc  # Or source ~/.zshrc
```

Or open a new terminal window.

> [!WARNING]  
> Important: Replace `"your_telegram_bot_token"` and `"your_chosen_auth_token"` with your actual tokens.

### 5. Configure the project
The `config/config.yaml` file allows you to customize the system's behavior.

### 6. Start the virtual environment
Activate the virtual environment created by uv:

```bash
source .venv/bin/activate  # For Bash/Zsh
```

### 7. Run the application
Start the main script:

```bash
python3 main.py
```

## Usage and Telegram Bot Commands
Once the application is running, you can interact with it through the Telegram bot.

* **Start the Bot**: Send the `/start` command to your Telegram bot.
* **Authenticate**: Send `/auth` to the bot. It will prompt you to enter your `AUTH_TOKEN`. This registers your Telegram user ID as an authorized user.
  
Available Commands:
* `/start`: Starts the bot.
* `/help`: Displays a help message with available commands.
* `/auth`: Authenticates the user with the provided AUTH_TOKEN.
* `/enroll`: Enrolls a new person in the system. You'll be prompted to provide a name and then send a photo of the person's face.
* `/list`: Lists all people enrolled in the system.
* `/remove`: Removes a person from the system (and deletes their face embedding).
* `/logout`: Removes authentication for the current user.


## Troubleshooting
* **Bot not responding**: Check that your `TELEGRAM_BOT_TOKEN` is correct and that your bot is still active on Telegram.
* **Camera not working**: Verify that the camera index (in `config.yaml`) is correct. You might need to experiment with different indices (0, 1, 2, etc.) to find the right one. Use fake_camera_mode and a video file to test if you're unsure about camera indices.
* **Dependency issues**: If you encounter problems after modifying dependencies, try removing the `.venv` directory and running `uv sync` again.
* **Errors during execution**: Check the console output and the log file (if enabled) for error messages. These messages can provide clues about the cause of the problem.

## Additional Notes
Due European AI Act & GDPR compliance's, you may not use this software for any surveillance purposes. This project is intended for educational and non-commercial use only. Any different use is at your own risk.
