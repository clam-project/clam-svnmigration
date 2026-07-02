svn co https://clam-project.org/clam/trunk/clam
cd clam

SVN_URL=$(svn info --show-item url)
SVN_PROJECT_URL="${SVN_URL%/trunk}"

svn log -q "$SVN_PROJECT_URL" \
  | awk -F'|' '/^r[0-9]+/ {
      gsub(/^ +| +$/, "", $2);
      print $2 " = " $2 " <" $2 "@example.invalid>"
    }' \
  | sort -u > authors.txt

# Edit authors.txt before continuing.

git svn clone "$SVN_PROJECT_URL" \
  --stdlayout \
  --prefix=svn/ \
  --authors-file=authors.txt \
  migrated-git

cd migrated-git

git checkout -b main svn/trunk

for ref in $(git for-each-ref --format='%(refname:short)' refs/remotes/svn/branches); do
  branch=${ref#svn/branches/}
  git branch "$branch" "$ref"
done

for ref in $(git for-each-ref --format='%(refname:short)' refs/remotes/svn/tags); do
  tag=${ref#svn/tags/}
  git tag "$tag" "$ref"
done

git lfs install --local

git lfs migrate import \
  --everything \
  --include="*" \
  --exclude=".gitattributes" \
  --object-map=lfs-object-map.csv

git lfs checkout

git remote add origin git@github.com:ORG/REPO.git
git push origin --all
git push origin --tags
git lfs push origin --all
