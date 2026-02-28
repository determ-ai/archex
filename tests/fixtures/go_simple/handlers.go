package main

import (
	"net/http"
	_ "embed"
)

type Handler interface {
	ServeHTTP(w http.ResponseWriter, r *http.Request)
}

type Middleware interface {
	Wrap(next Handler) Handler
}

type router struct {
	routes map[string]Handler
}

func NewRouter() *router {
	return &router{routes: make(map[string]Handler)}
}

func (r *router) AddRoute(path string, h Handler) {
	r.routes[path] = h
}

func (r *router) handle(path string) Handler {
	return r.routes[path]
}

func respondJSON(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
}
