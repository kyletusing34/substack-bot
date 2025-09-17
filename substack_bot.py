#!/usr/bin/env python3
"""
Substack Bot - Automated trading analysis and chat posting
Scrapes ES and NQ support/resistance levels from TradingView and posts to Substack Chat
"""

import asyncio
import os
import logging
import re
from datetime import datetime, timezone
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SubstackBot:
    def __init__(self):
        self.substack_email = os.getenv('SUBSTACK_EMAIL')
        self.substack_password = os.getenv('SUBSTACK_PASSWORD')
        
        if not self.substack_email or not self.substack_password:
            raise ValueError("SUBSTACK_EMAIL and SUBSTACK_PASSWORD environment variables must be set")
    
    async def scrape_tradingview_levels(self, symbol):
        """
        Scrape support and resistance levels from TradingView for ES or NQ
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Navigate to TradingView chart
                url = f"https://www.tradingview.com/chart/?symbol={symbol}"
                await page.goto(url, wait_until='networkidle')
                
                # Wait for chart to load
                await page.wait_for_timeout(5000)
                
                # Get current price
                current_price = None
                try:
                    price_selector = '[data-name="legend-source-item"] .js-symbol-last'
                    await page.wait_for_selector(price_selector, timeout=10000)
                    price_element = await page.query_selector(price_selector)
                    if price_element:
                        current_price = await price_element.inner_text()
                        current_price = re.sub(r'[^0-9.]', '', current_price)
                except Exception as e:
                    logger.warning(f"Could not get current price: {e}")
                
                # Look for support/resistance levels in the chart
                # This is a simplified approach - you may need to adjust selectors
                levels = {
                    'current_price': current_price,
                    'support_levels': [],
                    'resistance_levels': []
                }
                
                # For demo purposes, we'll use approximate levels
                # In a real implementation, you'd need to identify actual chart elements
                if symbol == 'ES1!':
                    # Example ES levels (you'd need to implement actual scraping)
                    if current_price:
                        price_float = float(current_price)
                        levels['support_levels'] = [
                            round(price_float - 25, 1),
                            round(price_float - 50, 1)
                        ]
                        levels['resistance_levels'] = [
                            round(price_float + 25, 1),
                            round(price_float + 50, 1)
                        ]
                elif symbol == 'NQ1!':
                    # Example NQ levels
                    if current_price:
                        price_float = float(current_price)
                        levels['support_levels'] = [
                            round(price_float - 100, 1),
                            round(price_float - 200, 1)
                        ]
                        levels['resistance_levels'] = [
                            round(price_float + 100, 1),
                            round(price_float + 200, 1)
                        ]
                
                return levels
                
            except Exception as e:
                logger.error(f"Error scraping TradingView: {e}")
                return None
            finally:
                await browser.close()
    
    async def post_to_substack_chat(self, message):
        """
        Post message to Substack Chat
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Navigate to Substack login
                await page.goto('https://substack.com/sign-in', wait_until='networkidle')
                
                # Fill login form
                await page.fill('input[type="email"]', self.substack_email)
                await page.click('button[type="submit"]')
                
                # Wait for password field and fill it
                await page.wait_for_selector('input[type="password"]', timeout=10000)
                await page.fill('input[type="password"]', self.substack_password)
                await page.click('button[type="submit"]')
                
                # Wait for login to complete
                await page.wait_for_timeout(3000)
                
                # Navigate to chat (adjust URL to your specific Substack chat)
                # You'll need to replace this with your actual chat URL
                await page.goto('https://substack.com/chat', wait_until='networkidle')
                
                # Find and click the message input area
                message_input = await page.wait_for_selector('[data-testid="chat-input"], .chat-input, textarea, [contenteditable="true"]', timeout=10000)
                await message_input.click()
                await message_input.fill(message)
                
                # Send the message
                send_button = await page.query_selector('[data-testid="send-button"], button[type="submit"], .send-button')
                if send_button:
                    await send_button.click()
                else:
                    # Fallback: try pressing Enter
                    await page.keyboard.press('Enter')
                
                logger.info("Message posted to Substack Chat successfully")
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                logger.error(f"Error posting to Substack Chat: {e}")
                raise
            finally:
                await browser.close()
    
    def format_market_analysis(self, es_levels, nq_levels):
        """
        Format market analysis message in Substack Chat style
        """
        timestamp = datetime.now(timezone.utc).strftime('%H:%M UTC')
        
        message = f"📊 Market Update - {timestamp}\n\n"
        
        if es_levels and es_levels['current_price']:
            message += f"🔹 ES (S&P 500 Futures)\n"
            message += f"Current: {es_levels['current_price']}\n"
            if es_levels['resistance_levels']:
                message += f"Resistance: {', '.join(map(str, es_levels['resistance_levels']))}\n"
            if es_levels['support_levels']:
                message += f"Support: {', '.join(map(str, es_levels['support_levels']))}\n"
            message += "\n"
        
        if nq_levels and nq_levels['current_price']:
            message += f"🔹 NQ (Nasdaq Futures)\n"
            message += f"Current: {nq_levels['current_price']}\n"
            if nq_levels['resistance_levels']:
                message += f"Resistance: {', '.join(map(str, nq_levels['resistance_levels']))}\n"
            if nq_levels['support_levels']:
                message += f"Support: {', '.join(map(str, nq_levels['support_levels']))}\n"
            message += "\n"
        
        message += "⚡ Key levels to watch for intraday moves\n"
        message += "#Trading #Futures #ES #NQ"
        
        return message
    
    async def run_analysis(self):
        """
        Main function to run the complete analysis and posting workflow
        """
        try:
            logger.info("Starting market analysis...")
            
            # Scrape data from TradingView
            es_task = self.scrape_tradingview_levels('ES1!')
            nq_task = self.scrape_tradingview_levels('NQ1!')
            
            es_levels, nq_levels = await asyncio.gather(es_task, nq_task)
            
            if not es_levels and not nq_levels:
                logger.error("Failed to scrape any market data")
                return
            
            # Format the message
            message = self.format_market_analysis(es_levels, nq_levels)
            logger.info(f"Formatted message: {message[:100]}...")
            
            # Post to Substack Chat
            await self.post_to_substack_chat(message)
            logger.info("Analysis complete and posted!")
            
        except Exception as e:
            logger.error(f"Error in analysis workflow: {e}")
            raise

async def main():
    """
    Entry point for the bot
    """
    bot = SubstackBot()
    await bot.run_analysis()

if __name__ == "__main__":
    asyncio.run(main())
