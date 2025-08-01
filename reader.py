#!/usr/bin/env python3

import random
from metadata import Metadata, parse_card_line
from generator import Generator


# This gives me the chat title, or the first and maybe last
# name of the user as fallback if it's a private chat
def get_chat_title(chat):
    if chat.title is not None:
        return chat.title
    elif chat.first_name is not None:
        if chat.last_name is not None:
            return chat.first_name + " " + chat.last_name
        else:
            return chat.first_name
    else:
        return ""


class Memory(object):
    def __init__(self, mid, content):
        self.id = mid
        self.content = content


# This is a chat Reader object, in charge of managing the parsing of messages
# for a specific chat, and holding said chat's metadata
class Reader(object):
    # Media tagging variables
    TAG_PREFIX = "^IS_"
    STICKER_TAG = "^IS_STICKER^"
    ANIM_TAG = "^IS_ANIMATION^"
    VIDEO_TAG = "^IS_VIDEO^"

    def __init__(self, metadata, vocab, min_period, max_period, logger, names=[]):
        # The Metadata object holding a chat's specific bot parameters
        self.meta = metadata
        # The Generator object holding the vocabulary learned so far
        self.vocab = vocab
        # The maximum period allowed for this bot
        self.max_period = max_period
        # The short term memory, for recently read messages (see below)
        self.short_term_mem = []
        # The countdown until the period ends and it's time to talk
        self.countdown = self.meta.period
        # The logger object shared program-wide
        self.logger = logger
        # The bot's nicknames + username
        self.names = names

    # Create a new Reader from a Chat object
    def FromChat(chat, min_period, max_period, logger):
        meta = Metadata(chat.id, chat.type, get_chat_title(chat))
        vocab = Generator()
        return Reader(meta, vocab, min_period, max_period, logger)

    # TODO: Create a new Reader from a whole Chat history
    def FromHistory(history, vocab, min_period, max_period, logger):
        return None

    # Create a new Reader from a meta's file dump
    def FromCard(card, vocab, min_period, max_period, logger):
        meta = Metadata.loads(card)
        return Reader(meta, vocab, min_period, max_period, logger)

    # Deprecated: this method will be removed in a new version
    def FromFile(text, min_period, max_period, logger, vocab=None):
        print("Warning! This method of loading a Reader from file (Reader.FromFile(...))",
              "is deprecated, and will be removed from the next update. Use FromCard instead.")

        # Load a Reader from a file's text string
        lines = text.splitlines()
        version = parse_card_line(lines[0]).strip()
        version = version if len(version.strip()) > 1 else lines[4]
        logger.info("Dictionary version: {} ({} lines)".format(version, len(lines)))
        if version == "v4" or version == "v5":
            return Reader.FromCard(text, vocab, min_period, max_period, logger)
            # I stopped saving the chat metadata and the cache together
        elif version == "v3":
            meta = Metadata.loadl(lines[0:8])
            cache = '\n'.join(lines[9:])
            vocab = Generator.loads(cache)
        elif version == "v2":
            meta = Metadata.loadl(lines[0:7])
            cache = '\n'.join(lines[8:])
            vocab = Generator.loads(cache)
        elif version == "dict:":
            meta = Metadata.loadl(lines[0:6])
            cache = '\n'.join(lines[6:])
            vocab = Generator.loads(cache)
        else:
            meta = Metadata.loadl(lines[0:4])
            cache = lines[4:]
            vocab = Generator(load=cache, mode=Generator.MODE_LIST)
            # raise SyntaxError("Reader: Metadata format unrecognized.")
        r = Reader(meta, vocab, min_period, max_period, logger)
        return r

    # Returns a nice lice little tuple package for the archivist to save to file.
    # Also commits to long term memory any pending short term memories
    def archive(self):
        self.commit_memory()
        return (self.meta.id, self.meta.dumps(), self.vocab.dumps())

    # Checks type. Returns "True" for "group" even if it's supergroupA
    def check_type(self, t):
        return t in self.meta.type

    # Hard check
    def exactly_type(self, t):
        return t == self.meta.type

    def set_title(self, title):
        self.meta.title = title

    # Sets a new period in the Metadata
    def set_period(self, period):
        # The period has to be in the range [min..max_period]; otherwise, clamp to said range
        new_period = max(self.min_period, min(period, self.max_period))
        set_period = self.meta.set_period(new_period)
        if new_period == set_period and new_period < self.countdown:
            # If succesfully changed and the new period is less than the current
            # remaining countdown, reduce the countdown to the new period
            self.countdown = new_period
        return new_period

    def set_answer(self, prob):
        return self.meta.set_answer(prob)

    def cid(self):
        return str(self.meta.id)

    def count(self):
        return self.meta.count

    def period(self):
        return self.meta.period

    def title(self):
        return self.meta.title

    def answer(self):
        return self.meta.answer

    def ctype(self):
        return self.meta.type

    def is_restricted(self):
        return self.meta.restricted

    def toggle_restrict(self):
        self.meta.restricted = (not self.meta.restricted)

    def is_silenced(self):
        return self.meta.silenced

    def toggle_silence(self):
        self.meta.silenced = (not self.meta.silenced)

    # Rolls the chance for answering in this specific chat,
    # according to the answer probability
    def is_answering(self):
        rand = random.random()
        chance = self.answer()
        if chance == 1:
            return True
        elif chance == 0:
            return False
        return rand <= chance

    # Adds a new message to the short term memory
    def add_memory(self, mid, content):
        mem = Memory(mid, content)
        self.short_term_mem.append(mem)

    # Returns a random message ID from the short memory,
    # when answering to a random comment
    def random_memory(self):
        if len(self.short_term_mem) == 0:
            return None
        mem = random.choice(self.short_term_mem)
        return mem.id

    def reset_countdown(self):
        self.countdown = self.meta.period

    # Reads a message
    # This process will determine which kind of message it is (Sticker, Anim,
    # Video, or actual text) and pre-process it accordingly for the Generator,
    # then store it in the short term memory
    def read(self, message):
        mid = str(message.message_id)

        if message.text is not None:
            self.learn(mid, message.text)
        elif message.sticker is not None:
            self.learn_drawing(mid, Reader.STICKER_TAG, message.sticker.file_id)
        elif message.animation is not None:
            self.learn_drawing(mid, Reader.ANIM_TAG, message.animation.file_id)
        elif message.video is not None:
            self.learn_drawing(mid, Reader.VIDEO_TAG, message.video.file_id)

        self.meta.count += 1

    # Stores a multimedia message in the short term memory as a text with
    # TAG + the media file ID
    def learn_drawing(self, mid, tag, drawing):
        self.learn(mid, tag + " " + drawing)

    # Stores a text message in the short term memory
    def learn(self, mid, text):
        for name in self.names:
            if name.casefold() in text.casefold() and len(text.split()) <= 3:
                # If it's less than 3 words and one of the bot's names is in
                # the message, ignore it as it's most probably just a summon
                return
        self.add_memory(mid, text)

    # Commits the short term memory messages into the "long term memory"
    # aka the vocabulary Generator's cache
    def commit_memory(self):
        for mem in self.short_term_mem:
            self.vocab.add(mem.content)
        self.short_term_mem = []

    def generate_message(self, max_len):
        return self.vocab.generate(size=max_len, silence=self.is_silenced())
