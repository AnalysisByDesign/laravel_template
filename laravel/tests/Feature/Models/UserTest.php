<?php

use App\Models\User;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Hash;

it('hashes the password when it is set', function () {
    $user = new User(['password' => 'secret-password']);

    expect($user->password)->not->toBe('secret-password')
        ->and(Hash::check('secret-password', $user->password))->toBeTrue();
});

it('casts email_verified_at to a date', function () {
    $user = new User;
    $user->email_verified_at = '2026-01-01 12:00:00';

    expect($user->email_verified_at)->toBeInstanceOf(Carbon::class);
});

it('hides the password and remember token when serialised', function () {
    $user = new User(['name' => 'A', 'email' => 'a@example.com', 'password' => 'secret-password']);
    $user->remember_token = 'token';

    expect($user->toArray())->not->toHaveKeys(['password', 'remember_token']);
});
