package main

import (
	"strings"
	"fmt"
)

const Version = "1.0.0"

func FormatName(first, last string) string {
	return strings.TrimSpace(first + " " + last)
}

func validateInput(input string) bool {
	return len(strings.TrimSpace(input)) > 0
}

func buildGreeting(name string) string {
	return fmt.Sprintf("Hello, %s!", name)
}
