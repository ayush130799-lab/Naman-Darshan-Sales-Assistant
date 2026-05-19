def sales_strategy(query):

    query = query.lower()

    if "price" in query:
        return """
Highlight value instead of only price.
Explain benefits and convenience.
"""

    elif "safe" in query:
        return """
Build trust and explain secure booking.
"""

    elif "later" in query:
        return """
Create urgency politely.
Mention limited slots.
"""

    else:
        return """
Act as a helpful sales assistant.
"""