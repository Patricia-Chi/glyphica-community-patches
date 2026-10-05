"""Register independent patches here. Apply and restore use a LIFO stack."""
from . import microsoft_shuangpin

PATCHES = {microsoft_shuangpin.ID: microsoft_shuangpin}
