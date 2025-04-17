import logging
from typing import Any, Dict, Optional, List
import asyncio
import aiohttp
import json
import os
import datetime

# TabTabTab library imports
from tabtabtab_lib.extension_interface import (
    ExtensionInterface,
    CopyResponse,
    PasteResponse,
    OnContextResponse,
    Notification,
    NotificationStatus,
    ImmediatePaste,
)

# LLM imports
from tabtabtab_lib.llm import LLMModel
from tabtabtab_lib.llm_interface import LLMProcessorInterface, LLMContext
from tabtabtab_lib.sse_interface import SSESenderInterface

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Define storage path for fashion ideas
FASHION_STORAGE_DIR = os.path.expanduser("~/fashion_ideas")

class FashionIdeasExtension(ExtensionInterface):
    """
    A TabTabTab extension for collecting fashion ideas from images and URLs.
    It saves fashion items you're interested in and organizes them for later viewing.
    """

    def __init__(self):
        super().__init__()
        # Create storage directory if it doesn't exist
        os.makedirs(FASHION_STORAGE_DIR, exist_ok=True)
        self.fashion_items = self._load_fashion_items()
        
    def _load_fashion_items(self) -> List[Dict]:
        """Load saved fashion items from storage"""
        storage_file = os.path.join(FASHION_STORAGE_DIR, "fashion_items.json")
        if os.path.exists(storage_file):
            try:
                with open(storage_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"Error loading fashion items: {e}")
        return []
    
    def _save_fashion_items(self):
        """Save fashion items to storage"""
        storage_file = os.path.join(FASHION_STORAGE_DIR, "fashion_items.json")
        try:
            with open(storage_file, "w") as f:
                json.dump(self.fashion_items, f)
        except Exception as e:
            log.error(f"Error saving fashion items: {e}")

    async def on_context_request(
        self, source_extension_id: str, context_query: Dict[str, Any]
    ) -> OnContextResponse:
        """Handle context requests from other extensions"""
        log.info(
            f"[{self.extension_id}] Received context request from '{source_extension_id}'"
        )

        # Return information about saved fashion items if requested
        if context_query.get("type") == "fashion_stats":
            stats = {
                "total_items": len(self.fashion_items),
                "categories": self._get_fashion_categories()
            }
            return OnContextResponse(
                contexts=[
                    OnContextResponse.ExtensionContext(
                        description="fashion_stats", 
                        context=json.dumps(stats)
                    )
                ]
            )

        return OnContextResponse(contexts=[])
    
    def _get_fashion_categories(self) -> Dict[str, int]:
        """Get counts of fashion items by category"""
        categories = {}
        for item in self.fashion_items:
            category = item.get("category", "uncategorized")
            categories[category] = categories.get(category, 0) + 1
        return categories

    async def on_copy(self, context: Dict[str, Any]) -> CopyResponse:
        """
        Process copy events to capture fashion ideas from URLs or screenshots.
        """
        log.info(f"[{self.extension_id}] on_copy called")

        device_id = context.get("device_id")
        request_id = context.get("request_id")
        window_info = context.get("window_info", {})
        browser_url = (
            window_info.get("accessibilityData", {}).get("browser_url")
            if isinstance(window_info, dict)
            else None
        )
        screenshot_data = context.get("screenshot_data")

        # Check if we have a URL or screenshot to process
        if browser_url and device_id and request_id:
            # Start background task to analyze the URL for fashion content
            asyncio.create_task(
                self._analyze_fashion_content(browser_url, device_id, request_id, screenshot_data)
            )
            
            return CopyResponse(
                notification=Notification(
                    request_id=request_id,
                    title="Fashion Ideas",
                    detail="Analyzing page for fashion content...",
                    content="",
                    status=NotificationStatus.PENDING,
                ),
            )
        elif screenshot_data and device_id and request_id:
            # Process screenshot data
            asyncio.create_task(
                self._analyze_screenshot(screenshot_data, device_id, request_id)
            )
            
            return CopyResponse(
                notification=Notification(
                    request_id=request_id,
                    title="Fashion Ideas",
                    detail="Analyzing image for fashion items...",
                    content="",
                    status=NotificationStatus.PENDING,
                ),
            )
            
        return CopyResponse()

    async def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        """
        Handle paste events to show fashion collection or add notes to items.
        """
        log.info(f"[{self.extension_id}] on_paste triggered")

        device_id = context.get("device_id")
        request_id = context.get("request_id")
        extensions_context = context.get("extensions_context", {})
        
        # Check if this is a request to view fashion collection
        command = extensions_context.get("command", "")
        if command == "show_collection":
            # Return a summary of saved fashion items
            return self._generate_collection_response(request_id)
        elif command == "add_note":
            # Add a note to a specific fashion item
            item_id = extensions_context.get("item_id")
            note = extensions_context.get("note")
            if item_id and note:
                return self._add_note_to_item(request_id, item_id, note)
                
        # Default response with instructions
        return PasteResponse(
            paste=Notification(
                request_id=request_id,
                title="Fashion Ideas",
                detail="Fashion Collection Helper",
                content="Commands:\n- show_collection: View your saved items\n- add_note: Add notes to items",
                status=NotificationStatus.READY,
            )
        )
    
    def _generate_collection_response(self, request_id: str) -> PasteResponse:
        """Generate a response showing the fashion collection"""
        if not self.fashion_items:
            return PasteResponse(
                paste=Notification(
                    request_id=request_id,
                    title="Fashion Ideas",
                    detail="Your collection is empty",
                    content="Start collecting fashion ideas by copying fashion websites or images!",
                    status=NotificationStatus.READY,
                )
            )
        
        # Create a formatted list of fashion items
        content = "Your Fashion Collection:\n\n"
        for i, item in enumerate(self.fashion_items[-10:]):  # Show last 10 items
            content += f"{i+1}. {item.get('title', 'Untitled')}\n"
            content += f"   Category: {item.get('category', 'Uncategorized')}\n"
            content += f"   Source: {item.get('source', 'Unknown')}\n"
            if item.get('notes'):
                content += f"   Notes: {item['notes']}\n"
            content += f"   Added: {item.get('date_added', 'Unknown')}\n\n"
        
        return PasteResponse(
            paste=Notification(
                request_id=request_id,
                title="Fashion Ideas",
                detail=f"Your collection ({len(self.fashion_items)} items)",
                content=content,
                status=NotificationStatus.READY,
            )
        )
    
    def _add_note_to_item(self, request_id: str, item_id: str, note: str) -> PasteResponse:
        """Add a note to a specific fashion item"""
        for item in self.fashion_items:
            if item.get("id") == item_id:
                item["notes"] = note
                self._save_fashion_items()
                return PasteResponse(
                    paste=Notification(
                        request_id=request_id,
                        title="Fashion Ideas",
                        detail="Note added successfully",
                        content=f"Added note to: {item.get('title', 'item')}",
                        status=NotificationStatus.READY,
                    )
                )
                
        return PasteResponse(
            paste=Notification(
                request_id=request_id,
                title="Fashion Ideas",
                detail="Error adding note",
                content="Could not find the specified item",
                status=NotificationStatus.ERROR,
            )
        )

    async def _analyze_fashion_content(
        self, url: str, device_id: str, request_id: str, screenshot_data: Optional[bytes] = None
    ) -> None:
        """
        Analyze a URL for fashion content using the LLM.
        If fashion content is found, save it to the collection.
        """
        log_prefix = f"[{self.extension_id}][Req:{request_id}]"
        log.info(f"{log_prefix} Analyzing URL for fashion content: {url}")

        # Fetch the page content
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30.0) as response:
                    if response.status == 200:
                        text_content = await response.text(encoding=response.charset or "utf-8", errors="ignore")
                    else:
                        log.error(f"{log_prefix} Failed to fetch URL: {response.status}")
                        await self.send_push_notification(
                            device_id=device_id,
                            notification=Notification(
                                request_id=request_id,
                                title="Fashion Ideas",
                                detail=f"Failed to fetch URL",
                                content="",
                                status=NotificationStatus.ERROR,
                            ),
                        )
                        return
        except Exception as e:
            log.error(f"{log_prefix} Error fetching URL content: {e}")
            return

        # Use LLM to determine if this is fashion-related content
        fashion_detection_prompt = """
        You are an AI assistant that specializes in identifying fashion content.
        Analyze the provided web page content and determine if it contains fashion items.
        If it does contain fashion items, extract the following information:
        1. Title/name of the fashion item(s)
        2. Category (clothing, accessories, shoes, etc.)
        3. Brief description of the item(s)
        4. Price information (if available)
        
        Respond in JSON format with the following structure:
        {
            "is_fashion": true/false,
            "items": [
                {
                    "title": "Item name",
                    "category": "Category",
                    "description": "Brief description",
                    "price": "Price (if available)"
                }
            ]
        }
        
        If the content is not fashion-related, simply return {"is_fashion": false}
        """

        if not self.llm_processor:
            log.error(f"{log_prefix} LLM Processor not configured")
            return

        try:
            log.info(f"{log_prefix} Using LLM to analyze fashion content...")
            llm_context = LLMContext(text=text_content)
            llm_response = await self.llm_processor.process(
                system_prompt=fashion_detection_prompt,
                message="Analyze this web page content for fashion items:",
                contexts=[llm_context],
                model=LLMModel.GEMINI_FLASH,
                stream=False,
            )
            
            # Parse the JSON response
            try:
                result = json.loads(llm_response)
                if result.get("is_fashion"):
                    # Save fashion items to collection
                    for item in result.get("items", []):
                        fashion_item = {
                            "id": f"item_{len(self.fashion_items)}_{int(datetime.datetime.now().timestamp())}",
                            "title": item.get("title", "Untitled fashion item"),
                            "category": item.get("category", "Uncategorized"),
                            "description": item.get("description", ""),
                            "price": item.get("price", "Unknown"),
                            "source": url,
                            "date_added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "has_image": screenshot_data is not None
                        }
                        
                        # Save screenshot if available
                        if screenshot_data:
                            image_filename = f"{fashion_item['id']}.png"
                            image_path = os.path.join(FASHION_STORAGE_DIR, image_filename)
                            with open(image_path, "wb") as f:
                                f.write(screenshot_data)
                            fashion_item["image_path"] = image_path
                        
                        self.fashion_items.append(fashion_item)
                    
                    self._save_fashion_items()
                    
                    # Notify the user
                    items_added = len(result.get("items", []))
                    await self.send_push_notification(
                        device_id=device_id,
                        notification=Notification(
                            request_id=request_id,
                            title="Fashion Ideas",
                            detail=f"Added {items_added} fashion item(s) to your collection!",
                            content=f"Successfully saved fashion items from {url}",
                            status=NotificationStatus.READY,
                        ),
                    )
                else:
                    # Not fashion content
                    await self.send_push_notification(
                        device_id=device_id,
                        notification=Notification(
                            request_id=request_id,
                            title="Fashion Ideas",
                            detail="No fashion content detected",
                            content="The page doesn't appear to contain fashion items.",
                            status=NotificationStatus.INFO,
                        ),
                    )
            except json.JSONDecodeError:
                log.error(f"{log_prefix} Failed to parse LLM response as JSON")
                
        except Exception as e:
            log.error(f"{log_prefix} Error during LLM processing: {e}")

    async def _analyze_screenshot(
        self, screenshot_data: bytes, device_id: str, request_id: str
    ) -> None:
        """
        Analyze a screenshot for fashion content and add to collection if relevant.
        In a real implementation, this would use image recognition.
        """
        log_prefix = f"[{self.extension_id}][Req:{request_id}]"
        log.info(f"{log_prefix} Analyzing screenshot for fashion items")
        
        # Since we don't have image recognition in this basic example,
        # we'll assume the screenshot is fashion-related and ask for details
        
        # Generate a fashion item entry
        fashion_item = {
            "id": f"item_{len(self.fashion_items)}_{int(datetime.datetime.now().timestamp())}",
            "title": "Screenshot fashion item",
            "category": "Uncategorized", 
            "description": "Fashion item from screenshot",
            "source": "Screenshot",
            "date_added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "has_image": True,
            "needs_details": True  # Flag that this item needs user input
        }
        
        # Save the screenshot
        image_filename = f"{fashion_item['id']}.png"
        image_path = os.path.join(FASHION_STORAGE_DIR, image_filename)
        with open(image_path, "wb") as f:
            f.write(screenshot_data)
        fashion_item["image_path"] = image_path
        
        # Add to collection
        self.fashion_items.append(fashion_item)
        self._save_fashion_items()
        
        # Send notification asking for details
        await self.send_push_notification(
            device_id=device_id,
            notification=Notification(
                request_id=request_id,
                title="Fashion Ideas",
                detail="Fashion item saved",
                content="Screenshot saved to your fashion collection.\n\n" +
                        "To add details, use the command:\n" +
                        f"add_note {fashion_item['id']} Your description here",
                status=NotificationStatus.READY,
            ),
        )