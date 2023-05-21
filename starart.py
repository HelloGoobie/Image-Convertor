import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageTk
from io import BytesIO
import uuid
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
from collections import Counter
import time
from sklearn.cluster import KMeans
from tktooltip import ToolTip

key_image_label = None
preview_label = None

def get_contrasting_color(hex_value):
    r, g, b = int(hex_value[1:3], 16), int(hex_value[3:5], 16), int(hex_value[5:7], 16)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "black" if brightness > 128 else "white"


def find_most_common_color(hex_values):
    color_counter = Counter(hex_values)
    most_common_color = color_counter.most_common(1)[0][0]
    return most_common_color


def convert_image_to_32x32(image_url, save_directory, enable_downsampling=False, convert_lower_colors=False):
    try:
        response = requests.get(image_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching image: {str(e)}")

    try:
        image = Image.open(BytesIO(response.content))
        image = image.convert("RGB")  # Convert the image to RGB mode

        # Check if image resolution is already 1:1
        width, height = image.size
        if width != height:
            min_size = min(width, height)
            new_width = min_size
            new_height = min_size
            left = (width - min_size) // 2
            top = (height - min_size) // 2
            right = (width + min_size) // 2
            bottom = (height + min_size) // 2
            image = image.crop((left, top, right, bottom))

            # Show warning message if image is cropped
            messagebox.showwarning("Image Cropped", "The original image was not 1:1.\n\nTo fit a 1:1 canvas, the image has been automatically cropped to the center point.\n\nIf you don't want the image cropped please try a different image that fits the 1:1 (square) resolution requirement")

        if enable_downsampling:
            image = image.resize((32, 32), resample=Image.NEAREST)  # Apply Nearest Neighbor Downsampling
        else:
            image = image.resize((32, 32))  # Default resizing

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

        # Perform color quantization using K-means clustering
        flattened_hex_values = [color for row in hex_values for color in row]
        k = min(10, len(set(flattened_hex_values)))  # Choose k as the minimum of 10 and the number of unique colors
        kmeans = KMeans(n_clusters=k, random_state=42).fit([[int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)] for c in flattened_hex_values])
        cluster_labels = kmeans.labels_
        cluster_centers = kmeans.cluster_centers_

        # Replace colors with the closest cluster center
        for y in range(image.height):
            for x in range(image.width):
                pixel_color = hex_values[y][x]
                pixel_rgb = [int(pixel_color[1:3], 16), int(pixel_color[3:5], 16), int(pixel_color[5:7], 16)]
                cluster_index = cluster_labels[y * image.width + x]
                closest_color = "#{:02x}{:02x}{:02x}".format(int(cluster_centers[cluster_index][0]), int(cluster_centers[cluster_index][1]), int(cluster_centers[cluster_index][2]))
                hex_values[y][x] = closest_color

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
        return save_path, key_image_path
    except Exception as e:
        raise Exception(f"Error converting image: {str(e)}")


def browse_save_directory():
    directory = filedialog.askdirectory()
    if directory:
        save_directory_entry.delete(0, tk.END)
        save_directory_entry.insert(tk.END, directory)


def show_conversion_completed_message(save_path):
    messagebox.showinfo("Conversion Completed", f"Image converted and saved at:\n{save_path}\n\nYou can now convert another image.")


def submit_conversion():
    global key_photo, key_image_label, preview_label

    image_url = image_url_entry.get()
    save_directory = save_directory_entry.get()
    enable_downsampling = downsampling_var.get()
    convert_lower_colors = lower_colors_var.get()

    if image_url and save_directory:
        submit_button.config(state=tk.DISABLED)  # Disable the submit button
        root.update_idletasks()  # Force update of the GUI

        if key_image_label:
            key_image_label.pack_forget()  # Remove the previous key image label
        if preview_label:
            preview_label.pack_forget()  # Remove the previous preview label

        save_path, key_image_path = convert_image_to_32x32(image_url, save_directory, enable_downsampling, convert_lower_colors)  # Perform the conversion
        show_conversion_completed_message(save_path)

        preview_label = tk.Label(root, text="Preview:")
        preview_label.pack()

        key_image = Image.open(key_image_path)
        key_image_preview = key_image.resize((300, 300), Image.LANCZOS)  # Resize the key image
        key_photo = ImageTk.PhotoImage(key_image_preview)
        key_image_label = tk.Label(root, image=key_photo)
        key_image_label.pack()

        submit_button.config(state=tk.NORMAL)  # Enable the submit button
    else:
        messagebox.showwarning("Incomplete Information", "Please enter an image URL and select a save directory.")


root = tk.Tk()
root.title("Goobie's Image Conversion")
root.geometry("500x700")

# Image URL entry
image_url_label = tk.Label(root, text="Image URL:")
image_url_label.pack()

image_url_entry = tk.Entry(root, width=50)
image_url_entry.pack()

image_url_entry.insert(tk.END, "Paste an image URL here")
image_url_entry.config(fg="gray")

# Save directory selection
save_directory_label = tk.Label(root, text="Save Directory:")
save_directory_label.pack()

save_directory_frame = tk.Frame(root)
save_directory_frame.pack()

browse_button = tk.Button(save_directory_frame, text="Browse", command=browse_save_directory)
browse_button.pack(side=tk.BOTTOM, pady=5)

save_directory_entry = tk.Entry(save_directory_frame, width=50)
save_directory_entry.pack(side=tk.BOTTOM, pady=5)

# Checkboxes
checkbox_frame = tk.Frame(root)
checkbox_frame.pack(pady=10)

downsampling_var = tk.BooleanVar()
downsampling_checkbox = tk.Checkbutton(root, text="Enable Nearest Neighbor Downsampling", variable=downsampling_var)
downsampling_checkbox.pack(anchor=tk.W, padx=10, pady=5)
ToolTip(downsampling_checkbox, msg="This sharpens the pixels when reducing the image size making for sharper pixels, use this if you are getting 'blurry' edges", follow=True)

lower_colors_var = tk.BooleanVar()
lower_colors_checkbox = tk.Checkbutton(root, text="Convert to Lower Amount of Colors", variable=lower_colors_var)
lower_colors_checkbox.pack(anchor=tk.W, padx=10, pady=5)
ToolTip(lower_colors_checkbox, msg="This reduces the number of colors in your artwork, making it less busy and complicated, while still maintaining its recognizability.", follow=True)

lower_colors_checkbox.pack(anchor=tk.W)

warning_label = tk.Label(root, text="Warning:\nConverting to lower amount of colors and downsampling \nthe image may not work 100% as intended\nPlay around with the settings to get the desired output")
warning_label.pack()

# Submit button
submit_button = tk.Button(root, text="Convert", command=submit_conversion)
submit_button.pack(pady=10)

watermark_label = tk.Label(root, text="Goobie's Image Conversion - 2023 - Version 1.0.1", justify=tk.CENTER, font=("Arial", 10), fg="gray")
watermark_label.pack(side=tk.BOTTOM, pady=10)

# Link to GitHub repo
github_link = tk.Label(root, text="GitHub: https://github.com/HelloGoobie/Image-Convertor", justify=tk.CENTER, font=("Arial", 10), fg="blue")
github_link.pack(side=tk.BOTTOM, pady=5)
github_link.bind("<Button-1>", lambda e: os.system("start " + "https://github.com/HelloGoobie/Image-Convertor"))


root.mainloop()
