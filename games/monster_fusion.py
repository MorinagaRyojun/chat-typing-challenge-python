import asyncio

class Game:
    def __init__(self, manager):
        self.manager = manager
        self.collected_parts = []

    async def handle_comment(self, comment_text: str):
        """Handles incoming chat comments."""
        if comment_text.lower().startswith("/monster "):
            part = comment_text[9:].strip()
            if part:
                self.collected_parts.append(part)
                await self.manager.broadcast({
                    "type": "parts_update",
                    "parts": self.collected_parts
                })

    async def generate_monster(self, api_choice: str):
        """Generates a monster from the collected parts."""
        if not self.collected_parts:
            await self.manager.broadcast({
                "type": "generation_error",
                "message": "No monster parts to generate from!"
            })
            return

        prompt = "A creature that is a mix of the following: " + ", ".join(self.collected_parts)
        print(f"Generated Prompt: {prompt}")

        # --- Mocking API Call ---
        await self.manager.broadcast({
            "type": "status_update",
            "message": f"Generating monster with {api_choice}..."
        })
        await asyncio.sleep(3) # Simulate API call delay

        # In a real scenario, you would call the API and save the image here.
        # For now, we'll use a placeholder.
        placeholder_image_path = "/static/placeholder_monster.png"

        self.collected_parts.clear()

        await self.manager.broadcast({
            "type": "monster_generated",
            "image_url": placeholder_image_path,
            "prompt": prompt
        })
        await self.manager.broadcast({
            "type": "parts_update", # Clear the parts list on the UI
            "parts": self.collected_parts
        })

    # This game doesn't have a leaderboard in the same way
    def get_leaderboard_data(self):
        return []
