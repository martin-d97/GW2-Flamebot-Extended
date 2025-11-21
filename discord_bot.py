import os
import re
import sys
import asyncio
import subprocess
import discord
from discord.ext import commands
from dotenv import load_dotenv
import tempfile
import uuid


load_dotenv()  
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(intents=intents, command_prefix="/")
def cleanup(temp_input_path, temp_output_path):
    try:
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
    except Exception as e:
        print(f"Failed to clean up temp files: {e}")
    return
def split_preserving_markup(text, limit=1900):
        # Split text into segments: fenced blocks (``` or ~~~) and normal text
        fence_pattern = re.compile(r'(```.*?```|~~~.*?~~~)', re.DOTALL)
        segments = []
        last = 0
        for m in fence_pattern.finditer(text):
            if m.start() > last:
                segments.append(("text", text[last:m.start()]))
            segments.append(("fenced", m.group(0)))
            last = m.end()
        if last < len(text):
            segments.append(("text", text[last:]))

        parts = []
        cur = ""

        def push_current():
            nonlocal cur
            if cur:
                parts.append(cur)
                cur = ""

        for typ, seg in segments:
            if typ == "text":
                s = seg
                while s:
                    space = limit - len(cur)
                    if space <= 0:
                        push_current()
                        space = limit
                    if len(s) <= space:
                        cur += s
                        break
                    # try to split at last newline within space
                    split_at = s.rfind('\n', 0, space)
                    if split_at == -1 or split_at < space // 2:
                        split_at = space
                    cur += s[:split_at]
                    s = s[split_at:]
                    s = s.lstrip('\n')
                    push_current()
            else:  # fenced block
                fence = seg
                # If it fits in current part, append
                if len(cur) + len(fence) <= limit:
                    cur += fence
                    continue
                # otherwise, start a new part
                push_current()
                # If fenced block itself is small enough, put it in its own part
                if len(fence) <= limit:
                    cur += fence
                    continue
                # Fenced block is larger than limit -> split its inner content but keep fences
                # Determine fence opener line and closing fence
                opener_end = fence.find('\n')
                if opener_end == -1:
                    opener = fence[:3]
                    opener_len = 3
                else:
                    opener = fence[:opener_end+1]
                    opener_len = opener_end+1
                # find the closing fence (last occurrence of ``` or ~~~)
                if fence.startswith('```'):
                    closing_idx = fence.rfind('```')
                    closing = '```'
                else:
                    closing_idx = fence.rfind('~~~')
                    closing = '~~~'
                # extract body between opener and closing
                body = fence[opener_len:closing_idx]
                trailer = fence[closing_idx:]
                # Calculate how much body we can place per fenced chunk
                wrapper_overhead = len(opener) + len(trailer)
                chunk_limit = max(100, limit - wrapper_overhead)
                i = 0
                while i < len(body):
                    chunk = body[i:i+chunk_limit]
                    # create a fenced chunk
                    chunk_block = opener + chunk + trailer
                    if len(chunk_block) > limit:
                        # As a last resort, hard-split the chunk to fit
                        chunk = chunk[:chunk_limit]
                        chunk_block = opener + chunk + trailer
                    parts.append(chunk_block)
                    i += chunk_limit
                cur = ""

        push_current()
        return parts




@bot.slash_command(name="flame", description="Run flame analysis for provided dps.report URL(s).")
async def flame(ctx, urls: str):
    """Run the flame analysis for one or more `https://dps.report/...` URLs passed as the `urls` option.

    Usage:
      `/flame urls:<urls>` - provide one or more URLs separated by spaces or newlines
    """

    await ctx.defer()

    # Extract URLs from the provided parameter
    provided_urls = re.findall(r'https?://dps.report\S+', urls or "")
    if not provided_urls:
        await ctx.followup.send("No valid dps.report URLs found in the `urls` option. Provide one or more `https://dps.report/...` URLs.")
        return

    # Generate unique temporary files for this request to avoid conflicts with concurrent requests
    unique_id = str(uuid.uuid4())
    temp_input_path = os.path.join(tempfile.gettempdir(), f"discord_temp_input_{unique_id}.txt")
    temp_output_path = os.path.join(tempfile.gettempdir(), f"Flame_Output_{unique_id}.txt")
    
    try:
        # Write temporary input file for the existing InputParser
        with open(temp_input_path, "w", encoding="utf-8") as f:
            for u in provided_urls:
                f.write(u.strip() + "\n")
    except Exception as e:
        await ctx.followup.send(f"Failed to write temp input file: {e}")
        return

    notify = await ctx.followup.send(f"Running analysis for {len(provided_urls)} URL(s)... This may take a few seconds.")

    # Run `main.py` as a separate subprocess to avoid importing grequests/gevent
    def run_main_subprocess():
        main_path = os.path.join(os.getcwd(), "main.py")
        try:
            # Set environment variable to tell main.py where to write output
            env = os.environ.copy()
            env["FLAME_OUTPUT_PATH"] = temp_output_path
            proc = subprocess.run([sys.executable, main_path, "-i", temp_input_path], cwd=os.getcwd(), capture_output=True, text=True, env=env)
            return proc
        except Exception:
            raise

    try:
        proc = await asyncio.get_running_loop().run_in_executor(None, run_main_subprocess)
    except Exception as e:
        await notify.edit(content=f"Error while running analysis: {e}")
        cleanup(temp_input_path, temp_output_path)
        return

    output = ""
    try:
        with open(temp_output_path, "r", encoding="utf-8") as f:
            output = f.read()
    except Exception as e:
        print(f"Failed to read output file: {e}")
        output = None
        await notify.edit(content="Analysis finished but produced no output.")
        cleanup(temp_input_path, temp_output_path)
        return

    # Discord limits messages to ~2000 chars. We send the output as multiple messages   
    parts = split_preserving_markup(output, limit=1900)
    
    if not parts:
        await notify.edit(content="Analysis finished but produced no output.")
        cleanup(temp_input_path, temp_output_path)
        return
    total = len(parts)
    await notify.edit(content=f"{parts[0]}")
    for i in range(1, total):
        await ctx.followup.send(f"{parts[i]}")
    
    # Clean up temp files after sending output
    cleanup(temp_input_path, temp_output_path)
 


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: Discord token not found. Ensure your .env contains DISCORD_TOKEN or set the environment variable.")
        sys.exit(1)
    bot.run(token)
