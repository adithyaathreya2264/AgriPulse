"""
The AgriPulse WhatsApp bot.

    routes/whatsapp_routes.py   the Twilio webhook (thin)
    whatsapp/bot.py             understands a message and decides what to do
    whatsapp/features/          one module per feature (weather, price, ...)
    whatsapp/state.py           conversation memory, duplicate + rate limiting
    whatsapp/twilio_io.py       sending messages, checking Twilio's signature
    whatsapp/media.py           downloading photos / voice notes, voice replies
    whatsapp/digest.py          the daily morning message

The bot logic works in English only. The webhook translates what the farmer
writes into English and the bot's answers back into their language.
"""
