"""BIO tags to character spans. Kept free of torch so the serving image can use it."""


def decode_spans(tags, offsets):
    """Per-token BIO tags -> [start, end, label] character spans.

    Tokens with (0, 0) offsets (special or padding) are skipped. Lenient like seqeval's default:
    an I- tag that does not continue a span of the same label starts a new span.
    """
    spans, current = [], None
    for tag, (start, end) in zip(tags, offsets):
        if start == end:
            continue
        if tag == "O":
            current = None
            continue
        prefix, label = tag.split("-", 1)
        if prefix == "I" and current is not None and current[2] == label:
            current[1] = end
        else:
            current = [start, end, label]
            spans.append(current)
    return spans
