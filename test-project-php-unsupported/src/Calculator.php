<?php

declare(strict_types=1);

namespace StitchQaFixture;

final class Calculator
{
    public function add(float $a, float $b): float
    {
        return $a + $b;
    }

    public function divide(float $a, float $b): float
    {
        return $a / $b;
    }

    public function average(array $values): float
    {
        return array_sum($values) / count($values);
    }
}
