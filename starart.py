import os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
from collections import Counter
import subprocess


def get_contrasting_color(hex_value):
    r, g, b = int(hex_value[1:3], 16), int(hex_value[3:5], 16), int(hex_value[5:7], 16)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "black" if brightness > 128 else "white"


def find_most_common_color(hex_values):
    color_counter = Counter(hex_values)
    most_common_color = color_counter.most_common(1)[0][0]
    return most_common_color


def convert_image_to_32x32(image_url, save_directory):
    try:
        response = requests.get(image_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching image: {str(e)}")

    try:
        image = Image.open(BytesIO(response.content))
        image = image.convert("RGB")  # Convert the image to RGB mode
        image = image.resize((32, 32))
        pixels = image.load()

        hex_values = []
        for y in range(image.height):
            hex_row = []
            for x in range(image.width):
                r, g, b = pixels[x, y]
                hex_value = "#{:02x}{:02x}{:02x}".format(r, g, b)  # Convert RGB to HEX
                hex_row.append(hex_value)
                pixel_info = f"{hex_value}"
                print(pixel_info, end=",")
            hex_values.append(hex_row)
            print()

        # Find the most common color
        most_common_color = find_most_common_color([color for row in hex_values for color in row])

        # Replace similar colors with the most common color
        for y in range(image.height):
            for x in range(image.width):
                if hex_values[y][x] != most_common_color:
                    if abs(int(hex_values[y][x][1:3], 16) - int(most_common_color[1:3], 16)) <= 16 and \
                            abs(int(hex_values[y][x][3:5], 16) - int(most_common_color[3:5], 16)) <= 16 and \
                            abs(int(hex_values[y][x][5:7], 16) - int(most_common_color[5:7], 16)) <= 16:
                        hex_values[y][x] = most_common_color

        # Save the converted 32x32px image
        unique_filename = str(uuid.uuid4())
        save_path = os.path.join(save_directory, unique_filename + ".png")
        image.save(save_path)
        # Create the key image
        square_size = min(3240 // image.width, 3240 // image.height)  # Calculate the maximum square size to fit the image
        key_image_width = square_size * image.width
        key_image_height = square_size * image.height
        key_image = Image.new("RGB", (key_image_width, key_image_height), color="white")
        key_draw = ImageDraw.Draw(key_image)
        font_size = min(square_size, 20)  # Choose a font size that fits the square size
        font = ImageFont.truetype("arial.ttf", font_size)

        for y, hex_row in enumerate(hex_values):
            for x, hex_value in enumerate(hex_row):
                square_x = x * square_size
                square_y = y * square_size
                key_draw.rectangle([(square_x, square_y), (square_x + square_size, square_y + square_size)], fill=hex_value)
                text_x = square_x + square_size // 2
                text_y = square_y + square_size // 2
                text_bbox = key_draw.textbbox((text_x, text_y), hex_value, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x -= text_width // 2
                text_y -= text_height // 2
                text_color = get_contrasting_color(hex_value)
                key_draw.text((text_x, text_y), hex_value, font=font, fill=text_color)

        # Save the key image
        key_image_path = os.path.splitext(save_path)[0] + "_key.png"
        key_image.save(key_image_path)

        print(f"Converted image saved successfully at: {save_path}")
        print(f"Key image saved successfully at: {key_image_path}")
        return save_path
    except Exception as e:
        raise Exception(f"Error converting image: {str(e)}")




def handle_submit(image_entry, save_directory, progress_bar, submit_button):
    image_url = image_entry.get()
    if not image_url:
        messagebox.showinfo("Error", "Please enter an image URL.")
        return

    save_dir = save_directory.get()
    if not save_dir:
        messagebox.showinfo("Error", "Please select a save location.")
        return

    submit_button.config(state="disabled")
    progress_bar.start()

    try:
        save_path = convert_image_to_32x32(image_url, save_dir)
        messagebox.showinfo("Success", "Image conversion completed successfully.")


    except Exception as e:
        messagebox.showinfo("Error", f"Image conversion failed: {str(e)}")
        print(f"Error: {str(e)}")

    progress_bar.stop()
    submit_button.config(state="normal")


def create_watermark(root):
    watermark_label = tk.Label(root, text="Created by Goobie\nhttps://github.com/HelloGoobie/Image-Convertor", font=("Arial", 8, "bold"), fg="#808080", bg="#F0F0F0")
    watermark_label.place(anchor="center", relx=0.5, rely=0.95)



# Create the main window
root = tk.Tk()
root.title("Goobie's Image Converter")
root.geometry("400x330")

# Image URL entry
image_prompt_label = tk.Label(root, text="Paste Image URL below:")
image_prompt_label.pack(pady=10)

image_entry = tk.Entry(root, width=40)
image_entry.pack()

# Save directory selection
save_directory = tk.StringVar()
save_directory.set(os.getcwd())  # Set default save directory to current working directory


def select_directory():
    chosen_dir = filedialog.askdirectory()
    if chosen_dir:
        save_directory.set(chosen_dir)


browse_button = tk.Button(root, text="Select Save Location", command=select_directory)
browse_button.pack(pady=10)

# Submit button
submit_button = tk.Button(root, text="Submit", command=lambda: handle_submit(image_entry, save_directory,
                                                                           progress_bar, submit_button))
submit_button.pack(pady=10)

# Progress bar
progress_bar = Progressbar(root, length=300, mode="indeterminate")
progress_bar.pack(pady=10)


# Run the main loop
root.mainloop()
