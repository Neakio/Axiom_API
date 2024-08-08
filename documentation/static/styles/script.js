function toggleSection(element) {
    const opblock = element.closest('.opblock');
    const isOpen = opblock.classList.contains('is-open');

    opblock.classList.toggle('is-open', !isOpen);
    opblock.classList.toggle('is-closd', isOpen);

    const button = opblock.querySelector('.opblock-control-arrow');
    button.setAttribute('aria-expanded', !isOpen);

    const arrow = button.querySelector('.arrow path');
    if (!isOpen) {
        arrow.setAttribute('d', 'M 17.418 14.908 C 17.69 15.176 18.127 15.176 18.397 14.908 C 18.667 14.64 18.668 14.207 18.397 13.939 L 10.489 6.109 C 10.219 5.841 9.782 5.841 9.51 6.109 L 1.602 13.939 C 1.332 14.207 1.332 14.64 1.602 14.908 C 1.873 15.176 2.311 15.176 2.581 14.908 L 10 7.767 L 17.418 14.908 Z');
    } else {
        arrow.setAttribute('d', 'M 17.418 5.092 C 17.69 4.824 18.127 4.824 18.397 5.092 C 18.667 5.36 18.668 5.793 18.397 6.061 L 10.489 13.891 C 10.219 14.159 9.782 14.159 9.51 13.891 L 1.602 6.061 C 1.332 5.793 1.332 5.36 1.602 5.092 C 1.873 4.824 2.311 4.824 2.581 5.092 L 10 12.233 L 17.418 5.092 Z');
    }

    // Toggle visibility of the immediate .no-margin div
    const noMarginDiv = opblock.querySelector('.no-margin');
    if (noMarginDiv) {
        noMarginDiv.style.display = isOpen ? 'none' : 'block';
    }
}

function stopPropagation(event) {
    event.stopPropagation();
}

function toggleContent(element) {
    const tagSection = element.closest('.opblock-tag-section');
    const isOpen = tagSection.classList.contains('is-open');
    console.log(tagSection)
    tagSection.classList.toggle('is-open', !isOpen);
    tagSection.classList.toggle('is-closed', isOpen);

    const button = tagSection.querySelector('button');
    button.setAttribute('aria-expanded', !isOpen);
    button.title = isOpen ? 'Expand operation' : 'Collapse operation';

    const arrow = button.querySelector('.arrow path');
    if (!isOpen) {
        arrow.setAttribute('d', 'M 17.418 14.908 C 17.69 15.176 18.127 15.176 18.397 14.908 C 18.667 14.64 18.668 14.207 18.397 13.939 L 10.489 6.109 C 10.219 5.841 9.782 5.841 9.51 6.109 L 1.602 13.939 C 1.332 14.207 1.332 14.64 1.602 14.908 C 1.873 15.176 2.311 15.176 2.581 14.908 L 10 7.767 L 17.418 14.908 Z');
    } else {
        arrow.setAttribute('d', 'M 17.418 5.092 C 17.69 4.824 18.127 4.824 18.397 5.092 C 18.667 5.36 18.668 5.793 18.397 6.061 L 10.489 13.891 C 10.219 14.159 9.782 14.159 9.51 13.891 L 1.602 6.061 C 1.332 5.793 1.332 5.36 1.602 5.092 C 1.873 4.824 2.311 4.824 2.581 5.092 L 10 12.233 L 17.418 5.092 Z');
    }
}


function toggleColumn(divId) {
    var div = document.getElementById(divId);
    var colToModify = div.querySelector('#myColgroup col:last-child');
    var button = div.querySelector('#toggleColumn');
    console.log(div)
    if (colToModify) {
        if (colToModify.style.visibility === 'collapse') {
            colToModify.style.visibility = 'visible';
            button.textContent = "Hide Commands";
        } else {
            colToModify.style.visibility = 'collapse';
            button.textContent = "Show Commands";
        }
    } else {
        console.log("Fourth <col> element not found.");
    }
}

function showTab(event, tabName) {
    const opblock = event.currentTarget.closest('.opblock');
    if (!opblock) return;

    opblock.querySelectorAll('.tab-item').forEach(tab => {
        tab.classList.remove('active');
    });
    opblock.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    const tabContent = opblock.querySelector(`#${tabName}`);
    if (tabContent) {
        event.currentTarget.classList.add('active');
        tabContent.classList.add('active');
    } else {
        console.error('Tab content not found for:', tabName);
    }
}