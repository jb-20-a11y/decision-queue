# AI use

Complete this file before submission. If a section does not apply, write `None`.

## Tools used

Repeat this section for each AI tool.

### [Tool name]

- **Tasks the tool assisted:** [Describe the tasks.]
- **Intermediate artifacts generated through AI use:** [List generated plans, drafts, code, tests, or other artifacts.]

```
class IntegerChoiceField(serializers.IntegerField):
    def __init__(self, choices, *args, **kwargs):
        self.choice_map = {label: val for val, label in choices}
        self.inverse_map = {val: label for val, label in choices}
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        # Convert integer from DB to choice text for reading
        return self.inverse_map.get(value, value)

    def to_internal_value(self, data):
        # Convert choice text from request to integer for writing
        if data in self.choice_map:
            return self.choice_map[data]
        # Fallback if an integer is passed directly
        if data in self.inverse_map:
            return data
        raise serializers.ValidationError("Invalid choice.")
```

- **Important output checked or changed:** [Describe what you reviewed, tested, corrected, rejected, or rewrote.]

## Final review

- [ ] I understand the important AI-assisted work in this repository.
- [ ] I checked or changed important AI output before submission.
- [ ] I did not include private or proprietary information in this file.

Do not include full prompt transcripts. They can contain personal, account, private, or proprietary information.
