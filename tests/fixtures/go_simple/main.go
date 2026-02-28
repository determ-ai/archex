package main

import (
	"fmt"
	"os"
)

func main() {
	cfg := LoadConfig()
	fmt.Println("starting server", cfg.Port)
	os.Exit(0)
}

func LoadConfig() *Config {
	return &Config{Port: 8080}
}
