# python-trigger-engine

## ffmpeg requirement

This project requires ffmpeg to be installed on the system.

### Windows

Download from:
https://www.gyan.dev/ffmpeg/builds/

Add ffmpeg/bin to PATH.

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install ffmpeg
```

## Recall Email Scheduling

To schedule the daily recall emails (9am, 12pm, 3pm, 6pm, 9pm) on the Oracle VM:

1. Deploy the code to `/opt/apps/python-trigger-engine/`.
2. Install the crontab:
   ```bash
   crontab /opt/apps/python-trigger-engine/application-source/crontab.txt
   ```
3. Verify the installation:
   ```bash
   crontab -l
   ```

Logs are written to `application-source/logs/cron.log`.
