<?php

declare(strict_types=1);

namespace StitchQaFixture\Tests;

use InvalidArgumentException;
use PHPUnit\Framework\TestCase;
use StitchQaFixture\Calculator;

final class CalculatorTest extends TestCase
{
    public function testAddWorks(): void
    {
        $calculator = new Calculator();
        self::assertSame(5.0, $calculator->add(2, 3));
    }

    public function testDivideWorks(): void
    {
        $calculator = new Calculator();
        self::assertSame(5.0, $calculator->divide(10, 2));
    }

    public function testDivideRejectsZero(): void
    {
        $calculator = new Calculator();

        $this->expectException(InvalidArgumentException::class);
        $calculator->divide(10, 0);
    }

    public function testAverageRejectsEmptyValues(): void
    {
        $calculator = new Calculator();

        $this->expectException(InvalidArgumentException::class);
        $calculator->average([]);
    }
}
