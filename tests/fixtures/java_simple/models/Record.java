public record Point(int x, int y) {
    public double distance() {
        return Math.sqrt(x * x + y * y);
    }
}
