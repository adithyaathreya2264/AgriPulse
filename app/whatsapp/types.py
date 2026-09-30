from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Incoming:
    """One WhatsApp message from a farmer (fields as Twilio sends them)."""

    phone: str                        # "+919876543210"
    body: str = ""
    sid: str | None = None
    media_url: str | None = None
    media_type: str = ""
    latitude: float | None = None
    longitude: float | None = None
    profile_name: str | None = None


@dataclass
class Outcome:
    """
    What the bot wants to say (English; the webhook translates it).

    replies   sent straight away
    deferred  slow work (prices, photo diagnosis, AI answers). When Twilio
              can send messages on its own, the webhook first sends `ack`
              and runs this in the background; otherwise it runs it before
              answering. Returns more English replies.
    static    the texts never change (menu, prompts): translations are cached
    voice     the farmer sent a voice note, so answer with a voice note too
    lang      the farmer's language code
    """

    replies: list[str] = field(default_factory=list)
    static: bool = False
    ack: str | None = None
    deferred: Callable[[], list[str]] | None = None
    voice: bool = False
    lang: str = "en"
    prefix: str = ""          # put before the first message ("🎤 You said: ...")


def say(*texts, static=False):
    return Outcome(replies=list(texts), static=static)


@dataclass
class Context:
    """Everything a feature needs to know about the conversation."""

    db: object
    incoming: Incoming
    phone: str                        # "+919876543210" (as WhatsApp gives it)
    phone10: str | None               # "9876543210": how accounts are keyed
    account: dict | None              # the AgriPulse user with this number
    wa_user: dict                     # bot preferences for this number
    session: dict                     # {"state": str | None, "data": dict}
    lang: str

    @property
    def state(self):
        return self.session.get("state")

    @property
    def data(self):
        return self.session.get("data", {})

    @property
    def district(self):
        """Best guess of the farmer's district (account first)."""
        if self.account and self.account.get("district"):
            return self.account["district"]

        return self.wa_user.get("digest_district")
