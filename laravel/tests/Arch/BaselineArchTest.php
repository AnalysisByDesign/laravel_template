<?php

/*
|--------------------------------------------------------------------------
| Baseline architecture rules
|--------------------------------------------------------------------------
|
| Rules every change keeps green. Spec-specific rules go in their own
| SpecNNNArchTest.php beside this file, so a rule can be traced back to the
| spec that introduced it.
*/

arch('no debugging calls are left in')
    ->expect(['dd', 'dump', 'ray', 'var_dump', 'print_r'])
    ->not->toBeUsed();

arch('controllers are suffixed')
    ->expect('App\Http\Controllers')
    ->toHaveSuffix('Controller');
