package main

import "encoding/json"

const MaxRetries = 3

const (
	StatusOK       = 200
	statusNotFound = 404
)

var DefaultTimeout = 30

type Config struct {
	Port    int
	Host    string
	Verbose bool
}

type User struct {
	Name  string
	Email string
	age   int
}

type unexportedModel struct {
	id   int
	data []byte
}

type ID = string

func (c *Config) Validate() error {
	if c.Port <= 0 {
		return fmt.Errorf("invalid port: %d", c.Port)
	}
	return nil
}

func (u User) ToJSON() ([]byte, error) {
	return json.Marshal(u)
}

var _ = json.Marshal
