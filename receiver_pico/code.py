from machine import Pin,SPI,PWM
import framebuf
import random
import time

BL = 13
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9


class LCD_1inch14(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 240
        self.height = 135

        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)

        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,1000_000)
        self.spi = SPI(1,10000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.init_display()

        self.red   =   0x07E0
        self.green =   0x001f
        self.blue  =   0xf800
        self.white =   0xffff

    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize dispaly"""
        self.rst(1)
        self.rst(0)
        self.rst(1)

        self.write_cmd(0x36)
        self.write_data(0x70)

        self.write_cmd(0x3A)
        self.write_data(0x05)

        self.write_cmd(0xB2)
        self.write_data(0x0C)
        self.write_data(0x0C)
        self.write_data(0x00)
        self.write_data(0x33)
        self.write_data(0x33)

        self.write_cmd(0xB7)
        self.write_data(0x35)

        self.write_cmd(0xBB)
        self.write_data(0x19)

        self.write_cmd(0xC0)
        self.write_data(0x2C)

        self.write_cmd(0xC2)
        self.write_data(0x01)

        self.write_cmd(0xC3)
        self.write_data(0x12)

        self.write_cmd(0xC4)
        self.write_data(0x20)

        self.write_cmd(0xC6)
        self.write_data(0x0F)

        self.write_cmd(0xD0)
        self.write_data(0xA4)
        self.write_data(0xA1)

        self.write_cmd(0xE0)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0D)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2B)
        self.write_data(0x3F)
        self.write_data(0x54)
        self.write_data(0x4C)
        self.write_data(0x18)
        self.write_data(0x0D)
        self.write_data(0x0B)
        self.write_data(0x1F)
        self.write_data(0x23)

        self.write_cmd(0xE1)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0C)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2C)
        self.write_data(0x3F)
        self.write_data(0x44)
        self.write_data(0x51)
        self.write_data(0x2F)
        self.write_data(0x1F)
        self.write_data(0x1F)
        self.write_data(0x20)
        self.write_data(0x23)

        self.write_cmd(0x21)

        self.write_cmd(0x11)

        self.write_cmd(0x29)

    def show(self):
        self.write_cmd(0x2A)
        self.write_data(0x00)
        self.write_data(0x28)
        self.write_data(0x01)
        self.write_data(0x17)

        self.write_cmd(0x2B)
        self.write_data(0x00)
        self.write_data(0x35)
        self.write_data(0x00)
        self.write_data(0xBB)

        self.write_cmd(0x2C)

        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

def set_pixels(pixels, snake_x, snake_y, apples, trail):
    for y_row in range(9):
        pixels.append([])
        for x_col in range(16):
            if x_col == snake_x and y_row == snake_y:
                pixels[y_row].append(LCD.green)
            elif [x_col, y_row] in trail:
                pixels[y_row].append(LCD.blue)
            elif [x_col, y_row] in apples:
                pixels[y_row].append(LCD.red)
            else:
                pixels[y_row].append(0)

if __name__=='__main__':
    pwm = PWM(Pin(BL))
    pwm.freq(1000)
    pwm.duty_u16(32768)

    LCD = LCD_1inch14()

    a_key = Pin(15,Pin.IN,Pin.PULL_UP)
    b_key = Pin(17,Pin.IN,Pin.PULL_UP)

    up_key = Pin(2 ,Pin.IN,Pin.PULL_UP) #上
    in_key = Pin(3 ,Pin.IN,Pin.PULL_UP)#中
    left_key = Pin(16 ,Pin.IN,Pin.PULL_UP)#左
    down_key = Pin(18 ,Pin.IN,Pin.PULL_UP)#下
    right_key = Pin(20 ,Pin.IN,Pin.PULL_UP)#右

    # Test setting the first row to green and everything else to black
    pixels = []

    snake_x = 9
    snake_y = 7
    direction = "right"

    loopi = 1
    score = 0
    trail = []
    apples = []

    set_pixels(pixels, snake_x - 1, snake_y - 1, apples, trail)

    while True:
        loopi += 1

        if up_key.value() == 0:
            direction = "up"
        elif down_key.value() == 0:
            direction = "down"
        elif left_key.value() == 0:
            direction = "left"
        elif right_key.value() == 0:
            direction = "right"

        # Are they at an apple?
        if [snake_x - 1, snake_y - 1] in apples:
            score += 5
            trail.append([snake_x-1,snake_y-1])
            apples = list(filter(lambda z : z != [snake_x - 1, snake_y - 1], apples))
        else:
            try:
                trail.pop(0)
            except IndexError:
                pass

        if loopi % 10 == 0:
            apples.append([random.randrange(1, 17), random.randrange(1, 10)])

        if direction == "up":
            pixels = []
            trail.append([snake_x-1, snake_y-1])
            snake_y -= 1
            set_pixels(pixels, snake_x - 1, snake_y - 1, apples, trail)
        elif direction == "down":
            pixels = []
            trail.append([snake_x-1, snake_y-1])
            snake_y += 1
            set_pixels(pixels, snake_x - 1, snake_y - 1, apples, trail)
        elif direction == "left":
            pixels = []
            trail.append([snake_x-1, snake_y-1])
            snake_x -= 1
            set_pixels(pixels, snake_x - 1, snake_y - 1, apples, trail)
        elif direction == "right":
            pixels = []
            trail.append([snake_x-1, snake_y-1])
            snake_x += 1
            set_pixels(pixels, snake_x - 1, snake_y - 1, apples, trail)

        # Reset the game if you hit a wall
        if snake_x in [0, 17]:
            snake_x = 9
            snake_y = 7
            score = 0
            trail = []
            apples = []
        elif snake_y in [0, 10]:
            snake_x = 9
            snake_y = 7
            score = 0
            trail = []
            apples = []
        # Reset the game if you run into yourself
        elif [snake_x-1, snake_y-1] in trail:
            snake_x = 9
            snake_y = 7
            score = 0
            trail = []
            apples = []


        # Graph/display the pixels
        for ii, row in enumerate(pixels):
            for i, col in enumerate(row):
                LCD.fill_rect(i * 15, ii * 15, 15, 15, col)

        LCD.text("Score: " + str(score), 0, 0, LCD.white)

        LCD.show()
        time.sleep(0.25)
