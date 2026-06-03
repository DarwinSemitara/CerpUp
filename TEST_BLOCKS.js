// Quick Test Script for Draggable Blocks
// Paste this into browser console after saving configuration

console.log('═══ DIAGNOSTIC TEST ═══');
console.log('');

// 1. Check if configuration saved
console.log('1️⃣ Configuration Status:');
console.log('  unitConfigSaved:', unitConfigSaved);
console.log('  subjectUnits:', subjectUnits);
console.log('');

// 2. Check current year/semester
console.log('2️⃣ Current Filter:');
console.log('  Year:', currentYear);
console.log('  Semester:', currentSemester);
console.log('  Key:', currentYear + '-' + currentSemester);
console.log('');

// 3. Check if subjects exist for this year/semester
console.log('3️⃣ Available Subjects:');
var key = currentYear + '-' + currentSemester;
var subjects = ALL_SUBJECTS[key] || [];
console.log('  Total subjects for', key + ':', subjects.length);
if (subjects.length > 0) {
    console.log('  First subject:', subjects[0]);
}
console.log('');

// 4. Check filtering logic
console.log('4️⃣ Filter Test:');
var availableSubjects = subjects.filter(function (subj) {
    var unitData = subjectUnits[subj.code];
    var hasData = !!unitData;
    var hasConfigured = hasData && unitData.configured > 0;
    var hasRemaining = hasData && unitData.allocated < unitData.configured;

    console.log('  ' + subj.code + ':',
        'hasData=' + hasData,
        'configured=' + (hasData ? unitData.configured : 'N/A'),
        'allocated=' + (hasData ? unitData.allocated : 'N/A'),
        'hasRemaining=' + hasRemaining
    );

    return hasData && unitData.configured > 0 && unitData.allocated < unitData.configured;
});
console.log('  ✅ Available subjects after filter:', availableSubjects.length);
console.log('');

// 5. Check container
console.log('5️⃣ Container Status:');
var container = document.getElementById('staging-blocks');
console.log('  Container found:', !!container);
if (container) {
    console.log('  Current HTML length:', container.innerHTML.length);
    console.log('  Current HTML preview:', container.innerHTML.substring(0, 100) + '...');
}
console.log('');

// 6. Test color function
console.log('6️⃣ Color Function Test:');
if (subjects.length > 0) {
    var testCode = subjects[0].code;
    var testColor = colorFor(testCode, currentYear, currentSemester);
    console.log('  Test subject:', testCode);
    console.log('  Generated color:', testColor);
}
console.log('');

// 7. Manual render attempt
console.log('7️⃣ Attempting Manual Render...');
try {
    renderDraggableBlocks();
    console.log('  ✅ Render completed without errors');
} catch (error) {
    console.error('  ❌ Render failed:', error);
}
console.log('');

console.log('═══ END DIAGNOSTIC ═══');
console.log('');
console.log('💡 If "Available subjects after filter" is 0, check the filter logic above');
console.log('💡 If container HTML length is < 500, blocks are not rendering');
console.log('💡 Share this output to diagnose the issue!');
