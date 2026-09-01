import discord
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import asyncio
import arabic_reshaper
from bidi.algorithm import get_display

def get_arabic_text(text):
    """Reshapes Arabic text to render properly via PIL"""
    if not isinstance(text, str):
        text = str(text)
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except Exception:
        return text

def create_leaderboard_image(users_data: list, server_name: str) -> BytesIO:
    """
    users_data format: [{'avatar_bytes': bytes, 'name': str, 'points': int, 'rank': int}, ...]
    """
    # UI Constants
    BG_COLOR = (23, 24, 28)
    PANEL_COLOR = (155, 62, 110)
    TEXT_COLOR = (255, 255, 255)
    PANEL_HEIGHT = 85
    PANEL_SPACING = 10
    PANEL_WIDTH = 750
    PADDING = 30
    
    total_panels = len(users_data)
    if total_panels == 0:
        total_height = 200
    else:
        total_height = PADDING * 2 + 50 + total_panels * (PANEL_HEIGHT + PANEL_SPACING) - PANEL_SPACING
        
    img = Image.new('RGB', (PANEL_WIDTH + PADDING * 2, total_height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("assets/fonts/Tajawal-Bold.ttf", 32)
        font_regular = ImageFont.truetype("assets/fonts/Tajawal-Bold.ttf", 24)
        font_small = ImageFont.truetype("assets/fonts/Tajawal-Bold.ttf", 20)
    except Exception as e:
        import traceback
        traceback.print_exc()
        font_large = ImageFont.load_default()
        font_regular = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw Title block background
    title_w, title_h = 200, 50
    title_x = PADDING + PANEL_WIDTH - title_w
    title_y = PADDING
    draw.rounded_rectangle([(title_x, title_y), (title_x + title_w, title_y + title_h)], radius=15, fill=(38, 59, 56))

    # Draw Title text (توب النقاط)
    title = "Top Points"
    draw.text((title_x + title_w - 20, title_y + 12), title, font=font_regular, fill=TEXT_COLOR, anchor="ra")

    y_offset = PADDING + title_h + 20
    for data in users_data:
        # Draw Panel (rounded rect)
        draw.rounded_rectangle(
            [(PADDING, y_offset), (PADDING + PANEL_WIDTH, y_offset + PANEL_HEIGHT)],
            radius=12, fill=PANEL_COLOR
        )

        # Avatar
        avatar_size = 65
        avatar_x = PADDING + 10
        avatar_y = y_offset + 10
        
        if data.get('avatar_bytes'):
            try:
                avatar_img = Image.open(BytesIO(data['avatar_bytes'])).convert("RGBA")
                avatar_img = avatar_img.resize((avatar_size, avatar_size))
                
                # Create circle mask
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                
                # Add white stroke outline ring
                stroke = Image.new("RGBA", (avatar_size + 4, avatar_size + 4), (255, 255, 255, 255))
                stroke_mask = Image.new("L", (avatar_size + 4, avatar_size + 4), 0)
                stroke_mask_draw = ImageDraw.Draw(stroke_mask)
                stroke_mask_draw.ellipse((0, 0, avatar_size + 4, avatar_size + 4), fill=255)
                
                # Apply mask and paste stroke
                out_stroke = Image.new("RGBA", (avatar_size + 4, avatar_size + 4))
                out_stroke.paste(stroke, (0, 0), stroke_mask)
                img.paste(out_stroke, (avatar_x - 2, avatar_y - 2), out_stroke)

                # Paste actual avatar inside outline
                out = Image.new("RGBA", (avatar_size, avatar_size))
                out.paste(avatar_img, (0, 0), mask)
                img.paste(out, (avatar_x, avatar_y), out)
                
            except Exception as e:
                # Fallback avatar
                draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), fill=(100,100,100))
        else:
            draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), fill=(100,100,100))

        # Rank number
        rank_str = f"#{data.get('rank', 0)}"
        draw.text((avatar_x + avatar_size + 15, y_offset + 15), rank_str, font=font_small, fill=(210, 210, 210))
        
        # Username
        name_str = str(data.get('name', 'Unknown'))
        draw.text((avatar_x + avatar_size + 15, y_offset + 42), name_str, font=font_regular, fill=TEXT_COLOR)
        
        # Points (arabic right aligned)
        points_str = f"{data.get('points', 0)} Points"
        draw.text((PADDING + PANEL_WIDTH - 20, y_offset + 30), points_str, font=font_regular, fill=TEXT_COLOR, anchor="ra")

        y_offset += PANEL_HEIGHT + PANEL_SPACING

    # Save to buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def create_rank_card(user_name: str, avatar_bytes: bytes, points: int, rank: int, level: int) -> BytesIO:
    """Creates a horizontal single-user rank card."""
    BG_COLOR = (23, 24, 28)
    PANEL_COLOR = (155, 62, 110)
    TEXT_COLOR = (255, 255, 255)
    
    img = Image.new('RGB', (600, 150), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("assets/fonts/Tajawal-Bold.ttf", 36)
        font_regular = ImageFont.truetype("assets/fonts/Tajawal-Bold.ttf", 24)
        font_small = ImageFont.truetype("assets/fonts/Tajawal-Bold.ttf", 20)
    except Exception:
        font_large = ImageFont.load_default()
        font_regular = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.rounded_rectangle([(15, 15), (585, 135)], radius=15, fill=PANEL_COLOR)

    # Avatar
    avatar_size = 90
    avatar_x, avatar_y = 30, 30
    if avatar_bytes:
        try:
            avatar_img = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
            avatar_img = avatar_img.resize((avatar_size, avatar_size))
            
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            stroke = Image.new("RGBA", (avatar_size + 6, avatar_size + 6), (255, 255, 255, 255))
            stroke_mask = Image.new("L", (avatar_size + 6, avatar_size + 6), 0)
            stroke_mask_draw = ImageDraw.Draw(stroke_mask)
            stroke_mask_draw.ellipse((0, 0, avatar_size + 6, avatar_size + 6), fill=255)
            
            out_stroke = Image.new("RGBA", (avatar_size + 6, avatar_size + 6))
            out_stroke.paste(stroke, (0, 0), stroke_mask)
            img.paste(out_stroke, (avatar_x - 3, avatar_y - 3), out_stroke)

            out = Image.new("RGBA", (avatar_size, avatar_size))
            out.paste(avatar_img, (0, 0), mask)
            img.paste(out, (avatar_x, avatar_y), out)
        except Exception:
            draw.ellipse((avatar_x, avatar_y, avatar_x+avatar_size, avatar_y+avatar_size), fill=(100,100,100))
            
    # Username and Level
    name = str(user_name)
    draw.text((avatar_x + avatar_size + 20, avatar_y + 10), name, font=font_large, fill=TEXT_COLOR)
    rank_str = f"#{rank} | Level {level}"
    draw.text((avatar_x + avatar_size + 20, avatar_y + 55), rank_str, font=font_small, fill=(200, 200, 200))
    
    # Points
    points_str = f"{points} Points"
    draw.text((560, avatar_y + 35), points_str, font=font_large, fill=TEXT_COLOR, anchor="ra")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

async def generate_leaderboard(users_data: list, server_name: str) -> discord.File:
    buffer = await asyncio.to_thread(create_leaderboard_image, users_data, server_name)
    return discord.File(fp=buffer, filename="leaderboard.png")

async def generate_rank_card(user_name: str, avatar_bytes: bytes, points: int, rank: int, level: int) -> discord.File:
    buffer = await asyncio.to_thread(create_rank_card, user_name, avatar_bytes, points, rank, level)
    return discord.File(fp=buffer, filename="rank.png")

import urllib.request

def fetch_avatar(url: str, size: int) -> Image.Image:
    """Fetch avatar from URL or return fallback image"""
    if not url:
        return Image.new("RGBA", (size, size), (147, 80, 115, 255))
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as u:
            raw_data = u.read()
        img = Image.open(BytesIO(raw_data)).convert('RGBA')
        try:
            resize_mode = Image.Resampling.LANCZOS
        except AttributeError:
            resize_mode = Image.ANTIALIAS
            
        img = img.resize((size, size), resize_mode)
        return img
    except Exception:
        return Image.new("RGBA", (size, size), (147, 80, 115, 255))

def make_circular(img: Image.Image) -> Image.Image:
    """Make image circular with transparent background"""
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
    
    output = Image.new('RGBA', img.size, (0, 0, 0, 0))
    output.paste(img, (0, 0))
    output.putalpha(mask)
    return output

def create_roulette_leaderboard_image(users_data: list, image_path: str = "assets/leaderboard.png") -> BytesIO:
    """Generate leaderboard image matching roulette bot dimensions and template"""
    img = Image.open(image_path).convert('RGBA')
    draw = ImageDraw.Draw(img)
    
    font_name = ImageFont.load_default(size=32)
    font_score = ImageFont.load_default(size=28)
    
    y_centers = [369, 420, 465, 510, 555, 605, 655, 700, 750, 800]
    av_size = 30
    
    for i, user in enumerate(users_data):
        if i >= len(y_centers):
            break
        
        y_center = y_centers[i] + 130
        
        # Avatar
        av_x = 270
        av_y = y_center - av_size // 2 - 2
        avatar_img = fetch_avatar(user.get("avatar_url"), av_size)
        circular_avatar = make_circular(avatar_img)
        img.paste(circular_avatar, (av_x, av_y), circular_avatar)
        
        # Name
        name_text = str(user.get('name', ''))
        if len(name_text) > 15:
            name_text = name_text[:14] + '...'
        try:
            reshaped = arabic_reshaper.reshape(name_text)
            bidi = get_display(reshaped)
        except Exception:
            bidi = name_text
        
        has_anchor = hasattr(draw, 'textlength')
        if has_anchor:
            draw.text((av_x + 50, y_center - 2), bidi, fill="white", font=font_name, anchor="lm")
        else:
            draw.text((av_x + 50, y_center - 15), bidi, fill="white", font=font_name)
            
        # Score
        score_val = user.get('score') if user.get('score') is not None else user.get('points', 0)
        s_text = str(score_val)
        if has_anchor:
            draw.text((1220, y_center - 3), s_text, fill="white", font=font_score, anchor="mm")
        else:
            draw.text((1200, y_center - 15), s_text, fill="white", font=font_score)
            
    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return output

async def generate_roulette_leaderboard(users_data: list, image_path: str = "assets/leaderboard.png") -> discord.File:
    buffer = await asyncio.to_thread(create_roulette_leaderboard_image, users_data, image_path)
    return discord.File(fp=buffer, filename="leaderboard.png")

